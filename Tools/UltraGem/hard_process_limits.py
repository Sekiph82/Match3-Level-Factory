"""OS-enforced CPU and committed-memory limits for isolated benchmark workers."""
from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys
import threading
from typing import Any


class HardLimitUnavailable(RuntimeError):
    """Raised before work starts when the requested OS limits cannot be installed."""


@dataclass(frozen=True)
class BoundedProcessOutcome:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    limits: dict[str, Any]
    cpu_limit_exceeded: bool = False


def _windows_job(memory_limit_bytes: int, cpu_time_limit_seconds: int):
    import ctypes
    from ctypes import wintypes

    SIZE_T = ctypes.c_size_t
    ULONG_PTR = ctypes.c_size_t

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", SIZE_T),
            ("MaximumWorkingSetSize", SIZE_T),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ULONG_PTR),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", SIZE_T),
            ("JobMemoryLimit", SIZE_T),
            ("PeakProcessMemoryUsed", SIZE_T),
            ("PeakJobMemoryUsed", SIZE_T),
        ]

    class CpuRateControlInformation(ctypes.Structure):
        _fields_ = [("ControlFlags", wintypes.DWORD), ("CpuRate", wintypes.DWORD)]

    class FileTime(ctypes.Structure):
        _fields_ = [("LowDateTime", wintypes.DWORD), ("HighDateTime", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ULONG_PTR), ctypes.POINTER(ULONG_PTR)]
    kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise HardLimitUnavailable(f"CreateJobObjectW failed: {ctypes.get_last_error()}")
    try:
        process_mask = ULONG_PTR()
        system_mask = ULONG_PTR()
        if not kernel32.GetProcessAffinityMask(kernel32.GetCurrentProcess(), ctypes.byref(process_mask), ctypes.byref(system_mask)):
            raise HardLimitUnavailable(f"GetProcessAffinityMask failed: {ctypes.get_last_error()}")
        allowed_mask = int(process_mask.value)
        if allowed_mask == 0:
            raise HardLimitUnavailable("No available processor affinity was reported.")
        one_core_mask = allowed_mask & -allowed_mask
        logical_cores = max(1, allowed_mask.bit_count())

        extended = ExtendedLimitInformation()
        basic = extended.BasicLimitInformation
        basic.PerProcessUserTimeLimit = cpu_time_limit_seconds * 10_000_000
        basic.PerJobUserTimeLimit = cpu_time_limit_seconds * 10_000_000
        basic.LimitFlags = 0x00000002 | 0x00000004 | 0x00000010 | 0x00000100 | 0x00000200 | 0x00002000
        basic.Affinity = one_core_mask
        extended.ProcessMemoryLimit = memory_limit_bytes
        extended.JobMemoryLimit = memory_limit_bytes
        if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(extended), ctypes.sizeof(extended)):
            raise HardLimitUnavailable(f"SetInformationJobObject(memory/time) failed: {ctypes.get_last_error()}")

        cpu_rate = CpuRateControlInformation()
        cpu_rate.ControlFlags = 0x1 | 0x4  # ENABLE | HARD_CAP
        cpu_rate.CpuRate = max(1, 10_000 // logical_cores)
        if not kernel32.SetInformationJobObject(job, 15, ctypes.byref(cpu_rate), ctypes.sizeof(cpu_rate)):
            raise HardLimitUnavailable(f"SetInformationJobObject(CPU hard cap) failed: {ctypes.get_last_error()}")

        def query_cpu_times(process_handle) -> tuple[int, int]:
            created, exited, kernel_time, user_time = (FileTime() for _ in range(4))
            if not kernel32.GetProcessTimes(process_handle, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel_time), ctypes.byref(user_time)):
                raise HardLimitUnavailable(f"GetProcessTimes failed: {ctypes.get_last_error()}")
            return ((int(user_time.HighDateTime) << 32) | int(user_time.LowDateTime),
                    (int(kernel_time.HighDateTime) << 32) | int(kernel_time.LowDateTime))

        def query_metrics(process_handle) -> dict[str, int]:
            measured = ExtendedLimitInformation()
            returned = wintypes.DWORD()
            if not kernel32.QueryInformationJobObject(job, 9, ctypes.byref(measured), ctypes.sizeof(measured), ctypes.byref(returned)):
                raise HardLimitUnavailable(f"QueryInformationJobObject(memory) failed: {ctypes.get_last_error()}")
            user_ticks, kernel_ticks = query_cpu_times(process_handle)
            return {
                "peakCommittedProcessBytes": int(measured.PeakProcessMemoryUsed),
                "peakCommittedJobBytes": int(measured.PeakJobMemoryUsed),
                "processUserCpuTime100ns": user_ticks,
                "processKernelCpuTime100ns": kernel_ticks,
            }

        return job, kernel32, query_metrics, query_cpu_times, {
            "backend": "windows_job_object",
            "hardCpuRateCap": True,
            "cpuRatePer10000MachineCycles": int(cpu_rate.CpuRate),
            "cpuAffinityLogicalCores": 1,
            "cpuTimeLimitSeconds": cpu_time_limit_seconds,
            "jobCpuTimeLimitSeconds": cpu_time_limit_seconds,
            "hardMemoryLimit": True,
            "jobMemoryLimitBytes": memory_limit_bytes,
            "committedMemoryLimitBytes": memory_limit_bytes,
        }
    except Exception:
        kernel32.CloseHandle(job)
        raise


def _apply_posix_limits(memory_limit_bytes: int, cpu_time_limit_seconds: int) -> None:
    import resource

    if not hasattr(resource, "RLIMIT_AS") or not hasattr(resource, "RLIMIT_CPU"):
        raise RuntimeError("Required POSIX RLIMIT_AS/RLIMIT_CPU controls are unavailable.")
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_time_limit_seconds, cpu_time_limit_seconds))
    if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
        allowed = os.sched_getaffinity(0)
        if not allowed:
            raise RuntimeError("No logical CPU is available for the isolated worker.")
        os.sched_setaffinity(0, {min(allowed)})


def run_limited_worker(command: list[str], *, timeout_seconds: float, env: dict[str, str],
                       memory_limit_bytes: int, cpu_time_limit_seconds: int) -> BoundedProcessOutcome:
    if os.name == "nt":
        import ctypes

        job, kernel32, query_metrics, query_cpu_times, limits = _windows_job(memory_limit_bytes, cpu_time_limit_seconds)
        process = None
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=env)
            process_handle = getattr(process, "_handle", None)
            if process_handle is None or not kernel32.AssignProcessToJobObject(job, process_handle):
                process.kill()
                process.communicate()
                raise HardLimitUnavailable(f"AssignProcessToJobObject failed: {ctypes.get_last_error()}")
            cpu_limit_hit = threading.Event()
            stop_monitor = threading.Event()
            cpu_limit_ticks = cpu_time_limit_seconds * 10_000_000

            def enforce_cpu_time_limit() -> None:
                while not stop_monitor.wait(0.01):
                    if process.poll() is not None:
                        return
                    user_ticks, kernel_ticks = query_cpu_times(process_handle)
                    if user_ticks + kernel_ticks >= cpu_limit_ticks:
                        cpu_limit_hit.set()
                        kernel32.TerminateJobObject(job, 0xE0000002)
                        return

            monitor = threading.Thread(target=enforce_cpu_time_limit, name="lfx-cpu-limit", daemon=True)
            monitor.start()
            try:
                stdout, stderr = process.communicate(input="RUN\n", timeout=timeout_seconds)
                timed_out = False
            except subprocess.TimeoutExpired:
                kernel32.TerminateJobObject(job, 0xE0000001)
                stdout, stderr = process.communicate()
                timed_out = True
            finally:
                stop_monitor.set()
                monitor.join(timeout=1)
            limits.update(query_metrics(process_handle))
            limits["cpuTimeWatchdogEnforced"] = True
            return BoundedProcessOutcome(process.returncode, stdout, stderr, timed_out, limits, cpu_limit_hit.is_set())
        finally:
            kernel32.CloseHandle(job)

    if os.name != "posix":
        raise HardLimitUnavailable(f"No hard process limit backend for {os.name}.")
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env,
                                   preexec_fn=lambda: _apply_posix_limits(memory_limit_bytes, cpu_time_limit_seconds))
    except (ImportError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise HardLimitUnavailable(f"POSIX hard resource limits could not be installed: {type(error).__name__}") from error
    try:
        stdout, stderr = process.communicate(input="RUN\n", timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        timed_out = True
    return BoundedProcessOutcome(process.returncode, stdout, stderr, timed_out, {
        "backend": "posix_rlimit",
        "hardCpuRateCap": False,
        "cpuTimeWatchdogEnforced": True,
        "cpuAffinityLogicalCores": 1 if hasattr(os, "sched_getaffinity") else None,
        "cpuTimeLimitSeconds": cpu_time_limit_seconds,
        "hardMemoryLimit": True,
        "memoryLimitKind": "virtual_address_space",
        "committedMemoryLimitBytes": memory_limit_bytes,
    })

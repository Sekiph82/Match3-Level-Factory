"""OS-resource and hard-wall-clock bounded LOCAL benchmark runner.

A fresh, isolated worker receives a fixed CPU-time budget and hard committed-
memory/address-space limit before benchmark imports begin. No Engine gameplay
claims are made; performance observations remain hardware-specific.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any
from hard_process_limits import HardLimitUnavailable, run_limited_worker

WORKER = Path(__file__).with_name('benchmark_worker.py')
OPERATIONS = ('features','canonical_hash','structural_compare')
EXPECTED_FIXTURE_SHA256 = 'fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d'
HARD_MEMORY_LIMIT_BYTES = 512 * 1024 * 1024
HARD_CPU_TIME_LIMIT_SECONDS = 5


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON property: {key}')
        result[key] = value
    return result


def run_bounded_baseline(*, iterations: int = 15, timeout_seconds: float = 10.0,
                         per_operation_budget_ms: float = 100.0) -> dict[str, Any]:
    if type(iterations) is not int or not 5 <= iterations <= 200:
        raise ValueError('iterations must be within 5..200')
    if type(timeout_seconds) not in (int,float) or not 0.1 <= timeout_seconds <= 60:
        raise ValueError('timeout must be within 0.1..60 seconds')
    if type(per_operation_budget_ms) not in (int,float) or not 0.01 <= per_operation_budget_ms <= 1_000_000:
        raise ValueError('observational per-op budget out of range')
    machine={'pythonVersion':platform.python_version(), 'platform':platform.platform(),
             'architecture':platform.machine(), 'cpuCount':os.cpu_count(),
             'measurementPortableBetweenMachines':False}
    collected=[]
    for operation in OPERATIONS:
        try:
            outcome=run_limited_worker([
                sys.executable,str(WORKER),'--operation',operation,
                '--iterations',str(iterations)],timeout_seconds=timeout_seconds,
                env={**os.environ,'PYTHONHASHSEED':'0','LFX_BENCHMARK_WAIT_FOR_LIMITS':'1'},
                memory_limit_bytes=HARD_MEMORY_LIMIT_BYTES,
                cpu_time_limit_seconds=HARD_CPU_TIME_LIMIT_SECONDS)
        except HardLimitUnavailable as error:
            collected.append({'operation':operation,'status':'UNKNOWN_RESOURCE_LIMIT_ENFORCEMENT',
                              'limitError':type(error).__name__,'limitErrorDetail':str(error),
                              'wallClockTimeoutEnforced':True,
                              'hardCpuTimeBudgetEnforced':False,'hardMemoryBudgetEnforced':False})
            continue
        limits=outcome.limits
        if outcome.cpu_limit_exceeded:
            collected.append({'operation':operation,'status':'UNKNOWN_CPU_TIME_LIMIT',
                              'wallClockTimeoutEnforced':True,'resourceLimits':limits,
                              'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        if outcome.timed_out:
            collected.append({'operation':operation,'status':'UNKNOWN_TIMEOUT_KILLED',
                              'wallClockTimeoutEnforced':True,'resourceLimits':limits,
                              'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        result=outcome
        if result.returncode!=0:
            collected.append({'operation':operation,'status':'UNKNOWN_WORKER_FAILURE',
                              'wallClockTimeoutEnforced':True,'exitCode':result.returncode,
                              'resourceLimits':limits,'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        try:
            body=json.loads(result.stdout,object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError,TypeError,ValueError):
            collected.append({'operation':operation,'status':'UNKNOWN_MALFORMED_RESULT',
                              'wallClockTimeoutEnforced':True,'resourceLimits':limits,
                              'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        if not isinstance(body,dict):
            collected.append({'operation':operation,'status':'UNKNOWN_UNTRUSTED_RESULT',
                              'wallClockTimeoutEnforced':True,'resourceLimits':limits,
                              'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        measurements=(body.get('medianMs'),body.get('p95Ms'),body.get('worstMs'))
        metric_ceiling_ms=timeout_seconds*1000
        peak_working_set=body.get('processPeakWorkingSetBytes')
        process_peak_memory=limits.get('peakCommittedProcessBytes',peak_working_set)
        if limits.get('backend')=='windows_job_object':
            cpu_user_seconds=limits.get('processUserCpuTime100ns',-1)/10_000_000
            cpu_kernel_seconds=limits.get('processKernelCpuTime100ns',-1)/10_000_000
        else:
            cpu_user_seconds=body.get('processUserCpuTimeSeconds')
            cpu_kernel_seconds=body.get('processKernelCpuTimeSeconds')
        metrics_valid=(all(type(value) in (int,float) and value>=0
                           and value<=metric_ceiling_ms
                           and (type(value) is int or math.isfinite(value))
                           for value in measurements)
                       and type(body.get('tracemallocPeakBytes')) is int
                       and body['tracemallocPeakBytes']>=0
                       and type(peak_working_set) is int and 0<=peak_working_set<=HARD_MEMORY_LIMIT_BYTES
                       and type(process_peak_memory) is int and 0<=process_peak_memory<=HARD_MEMORY_LIMIT_BYTES
                       and type(cpu_user_seconds) in (int,float) and math.isfinite(cpu_user_seconds)
                       and type(cpu_kernel_seconds) in (int,float) and math.isfinite(cpu_kernel_seconds)
                       and 0<=cpu_user_seconds+cpu_kernel_seconds<=HARD_CPU_TIME_LIMIT_SECONDS
                       and measurements[0]<=measurements[1]<=measurements[2])
        if (body.get('operation')!=operation or body.get('iterations')!=iterations
                or body.get('seed')!=712 or body.get('runtimeEngineSimulation') is not False
                or body.get('resultStillPrototypeOnly') is not True
                or body.get('inputDraftSha256')!=EXPECTED_FIXTURE_SHA256 or not metrics_valid):
            collected.append({'operation':operation,'status':'UNKNOWN_UNTRUSTED_RESULT',
                              'wallClockTimeoutEnforced':True,'resourceLimits':limits,
                              'hardCpuTimeBudgetEnforced':True,
                              'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True})
            continue
        collected.append({**body,'status':'OBSERVED_WITHIN_BUDGET' if body['p95Ms']<=per_operation_budget_ms
                          else 'OBSERVED_OVER_BUDGET','wallClockTimeoutEnforced':True,
                          'resourceLimits':limits,'hardCpuTimeBudgetEnforced':True,
                          'hardMemoryBudgetEnforced':limits.get('hardMemoryLimit') is True,
                          'processPeakCommittedBytes':process_peak_memory,
                          'processUserCpuTimeSeconds':round(cpu_user_seconds,7),
                          'processKernelCpuTimeSeconds':round(cpu_kernel_seconds,7)})
    return {
        'resultStatus':'REFERENCE_PERFORMANCE_BASELINE_ONLY',
        'engineStatus':'BLOCKED_ENG_M24',
        'sourceKind':'PINNED_SEED712_STATIC_DRAFT',
        'environment':machine,
        'perOperationBudgetMs':per_operation_budget_ms,
        'results':collected,
        'wallClockHardTimeoutPerWorker':timeout_seconds,
        'hardCpuTimeBudgetSecondsPerWorker':HARD_CPU_TIME_LIMIT_SECONDS,
        'hardMemoryBudgetBytesPerWorker':HARD_MEMORY_LIMIT_BYTES,
        'hardCpuTimeBudgetEnforced':all(item.get('hardCpuTimeBudgetEnforced') is True for item in collected),
        'hardMemoryBudgetEnforced':all(item.get('hardMemoryBudgetEnforced') is True for item in collected),
        'releaseAuthorized':False,
        'engineGameplayBenchmark':False,
    }

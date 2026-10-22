"""Start a child command only after its parent process has received OS limits.

Unity's batch test runner can log successful shutdown while an AssetImport
worker remains alive. For an explicitly configured Unity test, accept that
shutdown only when both the raw NUnit XML and exact Unity completion markers
prove success; then reap only the process tree launched by this wrapper.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree as ET


def _successful_unity_test(xml_path: Path, log_path: Path) -> bool:
    try:
        root = ET.parse(xml_path).getroot()
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ET.ParseError):
        return False
    try:
        total = int(root.attrib["total"])
        passed = int(root.attrib["passed"])
        failed = int(root.attrib["failed"])
        skipped = int(root.attrib["skipped"])
        inconclusive = int(root.attrib["inconclusive"])
    except (KeyError, ValueError):
        return False
    return (
        root.tag == "test-run"
        and root.attrib.get("result") == "Passed"
        and total > 0
        and passed == total
        and failed == skipped == inconclusive == 0
        and log.rfind("Test run completed. Exiting with code 0 (Ok). Run completed.")
        > log.rfind("Test run failed")
        and "Shut down." in log
    )


def _terminate_child_tree(process: subprocess.Popen[bytes]) -> int | None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    else:
        process.terminate()
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=5)


def _run_unity_test(command: list[str]) -> int:
    xml_path = Path(os.environ["LFX_UNITY_RESULT_XML"])
    log_path = Path(os.environ["LFX_UNITY_LOG_FILE"])
    grace_seconds = float(os.environ.get("LFX_UNITY_EXIT_GRACE_SECONDS", "8"))
    if not 1 <= grace_seconds <= 30:
        raise ValueError("Unity shutdown grace must be 1..30 seconds")
    if (Path(command[0]).name.lower() != "unity.exe" or "-runTests" not in command
            or str(xml_path) not in command or str(log_path) not in command):
        raise ValueError("bounded Unity test argv does not match the evidence paths")

    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    success_seen_at: float | None = None
    while True:
        exit_code = process.poll()
        if exit_code is not None:
            print(json.dumps({
                "childExecutable": Path(command[0]).name,
                "childExitCode": exit_code,
                "childInheritedJobLimits": True,
                "forcedCleanupAfterSuccessfulRunnerExit": False,
            }, sort_keys=True, separators=(",", ":")))
            return exit_code

        if _successful_unity_test(xml_path, log_path):
            if success_seen_at is None:
                success_seen_at = time.monotonic()
            elif time.monotonic() - success_seen_at >= grace_seconds:
                child_exit = _terminate_child_tree(process)
                print(json.dumps({
                    "childExecutable": Path(command[0]).name,
                    "childExitCode": child_exit,
                    "childInheritedJobLimits": True,
                    "runnerReportedExitCode": 0,
                    "nunitXmlPassed": True,
                    "forcedCleanupAfterSuccessfulRunnerExit": True,
                    "forcedCleanupReason": "Unity logged successful test completion and shutdown but retained a child process.",
                }, sort_keys=True, separators=(",", ":")))
                return 0
        else:
            success_seen_at = None
        time.sleep(0.25)


def main() -> int:
    if sys.stdin.readline().strip() != "RUN":
        return 70
    command = sys.argv[1:]
    if not command:
        return 64
    if "LFX_UNITY_RESULT_XML" in os.environ or "LFX_UNITY_LOG_FILE" in os.environ:
        if not {"LFX_UNITY_RESULT_XML", "LFX_UNITY_LOG_FILE"}.issubset(os.environ):
            return 65
        return _run_unity_test(command)
    completed = subprocess.run(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False)
    print(json.dumps({"childExecutable": Path(command[0]).name,
                      "childExitCode": completed.returncode,
                      "childInheritedJobLimits": True}, sort_keys=True, separators=(",", ":")))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

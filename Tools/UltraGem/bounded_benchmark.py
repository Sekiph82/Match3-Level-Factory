"""Hard-wall-clock bounded LOCAL benchmark runner, no Engine gameplay claims.

A new subprocess is used per static operation; the parent kills on timeout.
Memory is OBSERVED with tracemalloc, not a hard OS memory limit. Performance
budgets are only comparative on comparable hardware and Python versions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

WORKER = Path(__file__).with_name('benchmark_worker.py')
OPERATIONS = ('features','canonical_hash','structural_compare')


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
            result=subprocess.run([
                sys.executable,str(WORKER),'--operation',operation,
                '--iterations',str(iterations)],capture_output=True,text=True,
                timeout=timeout_seconds,check=False,env={**os.environ,'PYTHONHASHSEED':'0'})
        except subprocess.TimeoutExpired:
            collected.append({'operation':operation,'status':'UNKNOWN_TIMEOUT_KILLED','wallClockTimeoutEnforced':True})
            continue
        if result.returncode!=0:
            collected.append({'operation':operation,'status':'UNKNOWN_WORKER_FAILURE',
                              'wallClockTimeoutEnforced':True,'exitCode':result.returncode})
            continue
        try:
            body=json.loads(result.stdout)
        except (json.JSONDecodeError,TypeError):
            collected.append({'operation':operation,'status':'UNKNOWN_MALFORMED_RESULT',
                              'wallClockTimeoutEnforced':True})
            continue
        if (body.get('operation')!=operation or body.get('iterations')!=iterations
                or body.get('seed')!=712 or body.get('runtimeEngineSimulation') is not False
                or body.get('resultStillPrototypeOnly') is not True):
            collected.append({'operation':operation,'status':'UNKNOWN_UNTRUSTED_RESULT',
                              'wallClockTimeoutEnforced':True})
            continue
        collected.append({**body,'status':'OBSERVED_WITHIN_BUDGET' if body['p95Ms']<=per_operation_budget_ms
                          else 'OBSERVED_OVER_BUDGET','wallClockTimeoutEnforced':True})
    return {
        'resultStatus':'REFERENCE_PERFORMANCE_BASELINE_ONLY',
        'engineStatus':'BLOCKED_ENG_M24',
        'sourceKind':'PINNED_SEED712_STATIC_DRAFT',
        'environment':machine,
        'perOperationBudgetMs':per_operation_budget_ms,
        'results':collected,
        'wallClockHardTimeoutPerWorker':timeout_seconds,
        'hardMemoryBudgetEnforced':False,
        'releaseAuthorized':False,
        'engineGameplayBenchmark':False,
    }

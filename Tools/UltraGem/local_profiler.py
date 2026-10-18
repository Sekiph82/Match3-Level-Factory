"""Local diagnostic performance receipts outside canonical source hashes.

LFX-M07-006. Measuring wall time is intentionally non-deterministic. Metrics
are never embedded into source LevelDraft, ranked JSON, or accepted pack hash.
"""
from __future__ import annotations

import math
import time
import tracemalloc
from collections.abc import Callable
from typing import Any


def measure_local_operation(operation: Callable[[], Any], *, name: str,
                            invocation_budget_ms: float = 1000,
                            peak_memory_budget_bytes: int = 64_000_000) -> dict[str, Any]:
    if not callable(operation):
        raise ValueError("operation must be callable")
    if not isinstance(name,str) or not 1<=len(name)<=80 or not name.replace("_","").isalnum():
        raise ValueError("invalid operation identifier")
    if (isinstance(invocation_budget_ms,bool) or not isinstance(invocation_budget_ms,(int,float))
        or not math.isfinite(invocation_budget_ms) or not 1<=invocation_budget_ms<=3_600_000):
        raise ValueError("wall-time budget must be positive and bounded")
    if type(peak_memory_budget_bytes) is not int or not 1<=peak_memory_budget_bytes<=2_000_000_000:
        raise ValueError("memory budget must be a bounded integer")
    # Memory tracing is diagnostic only, NOT a resource fence. A caller is
    # responsible for process-level timeout / memory ceilings in real QA.
    tracemalloc.start()
    started=time.perf_counter()
    failed=None
    try:
        operation()
    except Exception as ex:
        failed=type(ex).__name__
    finally:
        elapsed=(time.perf_counter()-started)*1000
        _current,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return {
        "resultStatus":"LOCAL_PROFILING_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "operation":name,
        "elapsedMilliseconds":round(elapsed,4),
        "tracedPeakMemoryBytes":peak,
        "wallTimeBudgetMilliseconds":invocation_budget_ms,
        "tracedMemoryBudgetBytes":peak_memory_budget_bytes,
        "failureClass":failed,
        "budgetObservation":"FAILED_OPERATION" if failed else (
            "OBSERVED_OVER_BUDGET" if elapsed>invocation_budget_ms or peak>peak_memory_budget_bytes
            else "OBSERVED_WITHIN_BUDGET"),
        "hardProcessBudgetEnforced":False,
        "gameplayAcceptance":False,
    }

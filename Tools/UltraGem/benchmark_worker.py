"""Isolated fixed-seed static reference benchmark, for bounded_benchmark.py.

Worker is invoked only with immutable known fixture, never arbitrary code.
"""
from __future__ import annotations
import argparse
import json
import statistics
import time
import tracemalloc
from pathlib import Path

import candidate_diversity
import leveldraft
import reference_features

OPERATIONS = ('features', 'canonical_hash', 'structural_compare')
FIXTURE = Path(__file__).resolve().parents[2] / 'Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json'


def run(operation: str, iterations: int) -> dict:
    if operation not in OPERATIONS or type(iterations) is not int or not 5 <= iterations <= 200:
        raise ValueError('unsupported operation or bounded iterations')
    draft=leveldraft.loads_strict(FIXTURE.read_text(encoding='utf-8'))
    if draft['seed'] != 712:
        raise ValueError('fixture expected seed 712')
    funcs={
        'features':lambda:reference_features.extract_reference_features(draft),
        'canonical_hash':lambda:leveldraft.sha256(draft),
        'structural_compare':lambda:candidate_diversity.compare_drafts(draft,draft),
    }
    operation_call=funcs[operation]
    for _ in range(2): operation_call()
    tracemalloc.start()
    durations=[]
    last=None
    try:
        for _ in range(iterations):
            started=time.perf_counter_ns()
            last=operation_call()
            durations.append((time.perf_counter_ns()-started)/1_000_000)
        _current,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    # Results must never be hidden in synthetic 'PASS'; preserve real P95.
    measurements=sorted(durations)
    return {
        'operation':operation,'iterations':iterations,'seed':712,
        'inputDraftSha256':leveldraft.sha256(draft),
        'resultStillPrototypeOnly':True,
        'medianMs':round(statistics.median(measurements),6),
        'p95Ms':round(measurements[max(0, int(iterations*.95+.999999)-1)],6),
        'worstMs':round(max(measurements),6),
        'tracemallocPeakBytes':peak,
        'runtimeEngineSimulation':False,
        'lastResultStatus':last['engineStatus'] if isinstance(last,dict) and 'engineStatus' in last else 'STATIC_ONLY',
    }


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--operation',choices=OPERATIONS,required=True)
    p.add_argument('--iterations',type=int,default=15)
    args=p.parse_args(argv)
    print(json.dumps(run(args.operation,args.iterations),sort_keys=True,separators=(',',':')))

if __name__=='__main__': main()

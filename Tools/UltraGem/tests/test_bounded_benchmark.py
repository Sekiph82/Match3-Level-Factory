"""Real isolated subprocess baseline and fail-closed budget behavior."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bounded_benchmark import run_bounded_baseline

class BoundedBaselineTests(unittest.TestCase):
    def test_real_worker_fixed_seed_perf_observation(self):
        result=run_bounded_baseline(iterations=5,timeout_seconds=10)
        self.assertEqual(len(result['results']),3)
        self.assertFalse(result['hardMemoryBudgetEnforced'])
        self.assertFalse(result['engineGameplayBenchmark'])
        self.assertFalse(result['releaseAuthorized'])
        self.assertEqual(result['engineStatus'],'BLOCKED_ENG_M24')
        for item in result['results']:
            self.assertTrue(item['wallClockTimeoutEnforced'])
            self.assertIn(item['status'],('OBSERVED_WITHIN_BUDGET','OBSERVED_OVER_BUDGET'))
            self.assertEqual(item['seed'],712)
            self.assertEqual(item['inputDraftSha256'],
              'fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d')
            self.assertGreaterEqual(item['p95Ms'],0)
            self.assertGreaterEqual(item['tracemallocPeakBytes'],0)

    def test_timeout_does_not_count_as_pass(self):
        with patch('bounded_benchmark.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',.1)):
            result=run_bounded_baseline(iterations=5,timeout_seconds=.1)
        self.assertEqual([r['status'] for r in result['results']],['UNKNOWN_TIMEOUT_KILLED']*3)
        self.assertFalse(result['releaseAuthorized'])

    def test_nonzero_worker_exit_does_not_count_pass(self):
        failure=subprocess.CompletedProcess(args=['python'],returncode=1,stdout='',stderr='')
        with patch('bounded_benchmark.subprocess.run',return_value=failure):
            result=run_bounded_baseline(iterations=5)
        self.assertEqual([r['status'] for r in result['results']],['UNKNOWN_WORKER_FAILURE']*3)

    def test_invalid_budgets_do_not_start_worker(self):
        with self.assertRaises(ValueError):run_bounded_baseline(iterations=0)
        with self.assertRaises(ValueError):run_bounded_baseline(timeout_seconds=0)
        with self.assertRaises(ValueError):run_bounded_baseline(per_operation_budget_ms=float('nan'))

if __name__=='__main__':unittest.main()

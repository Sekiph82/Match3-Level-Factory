"""Real isolated subprocess baseline and fail-closed budget behavior."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bounded_benchmark import HARD_CPU_TIME_LIMIT_SECONDS, HARD_MEMORY_LIMIT_BYTES, run_bounded_baseline
from hard_process_limits import BoundedProcessOutcome, run_limited_worker

LIMITS={'backend':'test_hard_limit_backend','hardCpuRateCap':True,
        'cpuTimeLimitSeconds':5,'hardMemoryLimit':True,
        'committedMemoryLimitBytes':512*1024*1024,
        'peakCommittedProcessBytes':8*1024*1024,
        'processUserCpuTime100ns':100_000,'processKernelCpuTime100ns':100_000}

def limited(returncode=0,stdout='',stderr='',timed_out=False,limits=None):
    return BoundedProcessOutcome(returncode,stdout,stderr,timed_out,dict(limits or LIMITS))

class BoundedBaselineTests(unittest.TestCase):
    def test_real_worker_fixed_seed_perf_observation(self):
        result=run_bounded_baseline(iterations=5,timeout_seconds=10)
        self.assertEqual(len(result['results']),3)
        self.assertTrue(result['hardCpuTimeBudgetEnforced'])
        self.assertTrue(result['hardMemoryBudgetEnforced'])
        self.assertEqual(result['hardCpuTimeBudgetSecondsPerWorker'],HARD_CPU_TIME_LIMIT_SECONDS)
        self.assertEqual(result['hardMemoryBudgetBytesPerWorker'],HARD_MEMORY_LIMIT_BYTES)
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
            self.assertTrue(item['hardCpuTimeBudgetEnforced'])
            self.assertTrue(item['hardMemoryBudgetEnforced'])
            self.assertGreater(item['processPeakCommittedBytes'],0)
            self.assertLessEqual(item['processPeakCommittedBytes'],HARD_MEMORY_LIMIT_BYTES)
            self.assertLessEqual(item['processUserCpuTimeSeconds']+item['processKernelCpuTimeSeconds'],
                                 HARD_CPU_TIME_LIMIT_SECONDS)

    def test_timeout_does_not_count_as_pass(self):
        with patch('bounded_benchmark.run_limited_worker',return_value=limited(None,timed_out=True)):
            result=run_bounded_baseline(iterations=5,timeout_seconds=.1)
        self.assertEqual([r['status'] for r in result['results']],['UNKNOWN_TIMEOUT_KILLED']*3)
        self.assertFalse(result['releaseAuthorized'])

    def test_nonzero_worker_exit_does_not_count_pass(self):
        with patch('bounded_benchmark.run_limited_worker',return_value=limited(1)):
            result=run_bounded_baseline(iterations=5)
        self.assertEqual([r['status'] for r in result['results']],['UNKNOWN_WORKER_FAILURE']*3)

    def test_json_with_wrong_shape_or_invalid_metrics_does_not_crash_or_pass(self):
        for payload in ('[]', 'null', '{"operation":"features"}',
                        '{"medianMs":0,"p95Ms":NaN,"worstMs":1,"tracemallocPeakBytes":0}',
                        '{"medianMs":0,"p95Ms":1,"worstMs":' + ('9' * 400) + ',"tracemallocPeakBytes":0}'):
            with self.subTest(payload=payload),patch('bounded_benchmark.run_limited_worker',return_value=limited(stdout=payload)):
                result=run_bounded_baseline(iterations=5)
            self.assertEqual([r['status'] for r in result['results']],
                             ['UNKNOWN_UNTRUSTED_RESULT']*3)

    def test_worker_result_must_match_pinned_fixture_hash(self):
        results=[]
        for operation in ('features','canonical_hash','structural_compare'):
            body={'operation':operation,'iterations':5,'seed':712,
                  'runtimeEngineSimulation':False,'resultStillPrototypeOnly':True,
                  'inputDraftSha256':'0'*64,'medianMs':1,'p95Ms':1,'worstMs':1,
                  'tracemallocPeakBytes':10}
            results.append(limited(stdout=json.dumps(body)))
        with patch('bounded_benchmark.run_limited_worker',side_effect=results):
            result=run_bounded_baseline(iterations=5)
        self.assertEqual([item['status'] for item in result['results']],
                         ['UNKNOWN_UNTRUSTED_RESULT']*3)

    def test_duplicate_json_properties_are_rejected(self):
        with patch('bounded_benchmark.run_limited_worker',return_value=limited(
                stdout='{"operation":"features","operation":"canonical_hash"}')):
            result=run_bounded_baseline(iterations=5)
        self.assertEqual([item['status'] for item in result['results']],
                         ['UNKNOWN_MALFORMED_RESULT']*3)

    @unittest.skipUnless(sys.platform=='win32','Windows Job Object enforcement probe.')
    def test_windows_job_object_rejects_commit_over_budget_process(self):
        allocation_bytes=128*1024*1024
        outcome=run_limited_worker([sys.executable,'-c',
            'import sys; sys.stdin.readline(); payload=bytearray(' + str(allocation_bytes) + '); print(len(payload))'],
            timeout_seconds=8,env=dict(__import__('os').environ),
            memory_limit_bytes=32*1024*1024,cpu_time_limit_seconds=3)
        self.assertFalse(outcome.timed_out)
        self.assertEqual(outcome.limits['backend'],'windows_job_object')
        self.assertTrue(outcome.limits['hardMemoryLimit'])
        self.assertNotEqual(outcome.returncode,0)
        self.assertLessEqual(outcome.limits['peakCommittedProcessBytes'],32*1024*1024)

    @unittest.skipUnless(sys.platform=='win32','Windows Job Object enforcement probe.')
    def test_windows_job_object_stops_cpu_over_budget_process(self):
        outcome=run_limited_worker([sys.executable,'-c',
            'import sys; sys.stdin.readline(); value=0\nwhile True: value+=1'],
            timeout_seconds=8,env=dict(__import__('os').environ),
            memory_limit_bytes=HARD_MEMORY_LIMIT_BYTES,cpu_time_limit_seconds=1)
        self.assertFalse(outcome.timed_out)
        self.assertEqual(outcome.limits['backend'],'windows_job_object')
        self.assertTrue(outcome.limits['hardCpuRateCap'])
        self.assertNotEqual(outcome.returncode,0)
        cpu_seconds=(outcome.limits['processUserCpuTime100ns']+
                     outcome.limits['processKernelCpuTime100ns'])/10_000_000
        self.assertLessEqual(cpu_seconds,1.5)

    def test_invalid_budgets_do_not_start_worker(self):
        with self.assertRaises(ValueError):run_bounded_baseline(iterations=0)
        with self.assertRaises(ValueError):run_bounded_baseline(timeout_seconds=0)
        with self.assertRaises(ValueError):run_bounded_baseline(per_operation_budget_ms=float('nan'))

if __name__=='__main__':unittest.main()

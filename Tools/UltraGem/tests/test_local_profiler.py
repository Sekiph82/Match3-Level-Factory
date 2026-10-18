from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_profiler import measure_local_operation

class LocalProfilerTests(unittest.TestCase):
    def test_observation_has_explicit_non_enforced_budget_and_never_passes_engine(self):
        r=measure_local_operation(lambda:sum(range(100)),name="reference_features",
                                  invocation_budget_ms=1000)
        self.assertEqual(r["engineStatus"],"BLOCKED_ENG_M24")
        self.assertFalse(r["hardProcessBudgetEnforced"])
        self.assertFalse(r["gameplayAcceptance"])
        self.assertIn(r["budgetObservation"],{"OBSERVED_WITHIN_BUDGET","OBSERVED_OVER_BUDGET"})
        self.assertGreaterEqual(r["elapsedMilliseconds"],0)
        self.assertGreaterEqual(r["tracedPeakMemoryBytes"],0)
    def test_exceptions_are_recorded_as_failure_not_success(self):
        def broken():raise RuntimeError("expected probe")
        result=measure_local_operation(broken,name="failure_probe")
        self.assertEqual(result["failureClass"],"RuntimeError")
        self.assertEqual(result["budgetObservation"],"FAILED_OPERATION")
        for limit in (0,float("inf"),float("nan")):
            with self.assertRaises(ValueError):
                measure_local_operation(lambda:None,name="probe",invocation_budget_ms=limit)

if __name__=="__main__":unittest.main()

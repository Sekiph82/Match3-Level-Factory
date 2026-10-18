from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from failure_classification import (FAIL_EVENTS,UNKNOWN_EVENTS,classify_reference_failure)

class FailureClassificationTests(unittest.TestCase):
    def test_all_chaos_event_types_are_never_pass(self):
        for event in sorted(FAIL_EVENTS|UNKNOWN_EVENTS):
            with self.subTest(event=event):
                r=classify_reference_failure(event_id=event,observed=True,
                      evidence_reference="Drive/qa-chaos-case")
                self.assertIn(r["resultStatus"],{"FAIL","UNKNOWN"})
                self.assertNotEqual(r["resultStatus"],"PASS")
                self.assertFalse(r["acceptedGameplay"])
                self.assertFalse(r["releaseAuthorized"])
                if event in FAIL_EVENTS:self.assertEqual(r["resultStatus"],"FAIL")
        self.assertEqual(classify_reference_failure(event_id="ILLEGAL_MOVE",observed=False)["resultStatus"],"UNKNOWN")
    def test_fake_certification_and_unknown_reason_rejected(self):
        for fake in ("PASS","SIMULATION_SUCCESS","PAID_BOOSTER"):
            with self.assertRaises(ValueError):
                classify_reference_failure(event_id=fake,observed=True)
        with self.assertRaises(ValueError):
            classify_reference_failure(event_id="TIMEOUT",observed=1)

if __name__=="__main__":unittest.main()

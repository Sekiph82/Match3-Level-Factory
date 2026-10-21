from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from capture_local_session import capture_cancel_resume, summarize_ledger
from profile_compatibility import PROFILE_IDS


class CaptureLocalSessionTests(unittest.TestCase):
    def test_mixed_event_and_status_rows_are_summarized_without_key_error(self):
        self.assertEqual(
            summarize_ledger([
                {"event": "CANCEL_REQUESTED", "completed": 1},
                {"status": "CANCELLED"},
                {"status": "COMPLETED"},
            ]),
            {"entryCount": 3, "labels": ["CANCEL_REQUESTED", "CANCELLED", "COMPLETED"]},
        )

    def test_real_bounded_capture_cancels_resumes_and_persists_event_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = capture_cancel_resume(root, "Artifacts/capture", PROFILE_IDS[0], 510000)
            run = root / "Artifacts/capture"
            ledger = json.loads((run / "capture-ledger.json").read_text(encoding="utf-8"))["entries"]
            self.assertEqual(result["result"], "CAPTURED_LOCAL_SAMPLE_ONLY")
            self.assertEqual(result["ledgerSummary"]["labels"], ["CANCEL_REQUESTED", "CANCELLED", "COMPLETED"])
            self.assertNotIn("status", ledger[0])
            self.assertEqual(result["candidateCount"], 2)
            self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
            self.assertEqual(result["engineQualifiedCampaignLevels"], 0)
            self.assertTrue((run / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()

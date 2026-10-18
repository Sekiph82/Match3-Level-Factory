"""LFX-M05-007: deterministic descriptive dashboard and false-PASS guards."""
from __future__ import annotations
import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference_dashboard import reference_csv, summarize_reference_records


class ReferenceDashboardTests(unittest.TestCase):
    def example(self):
        return [
            {"seed": 2, "persona": "random", "outcome": "REFERENCE_UNKNOWN", "movesUsed": 7, "score": 0},
            {"seed": 1, "persona": "smart", "outcome": "REFERENCE_COMPLETED", "movesUsed": 5, "score": 1200},
            {"seed": 3, "persona": "smart", "outcome": "REFERENCE_FAILED", "movesUsed": 10, "score": 12000},
        ]

    def test_distributions_include_unknown_and_are_stable(self):
        rows = self.example()
        untouched = copy.deepcopy(rows)
        result = summarize_reference_records(rows)
        self.assertEqual(rows, untouched)
        self.assertEqual(result["sampleCount"], 3)
        self.assertEqual(result["outcomes"]["REFERENCE_UNKNOWN"], 1)
        self.assertEqual(result["scoreHistogram"], {"0": 1, "1-999": 0, "1000-9999": 1, "10000+": 1})
        self.assertEqual(result["medianObservedScore"], 1200)
        self.assertEqual(result["byPersona"]["smart"]["meanMovesObserved"], 7.5)
        self.assertFalse(result["claimDifficultyOrWinProbability"])
        self.assertEqual(result["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(summarize_reference_records(rows), result)

    def test_csv_order_and_escaping_is_deterministic(self):
        rows = self.example()
        first = reference_csv(rows)
        self.assertEqual(first, reference_csv(list(reversed(rows))))
        self.assertEqual(first.splitlines()[0], "seed,persona,outcome,movesUsed,score")
        self.assertTrue(first.splitlines()[1].startswith("1,smart,"))
        self.assertTrue(first.endswith("\n"))

    def test_adversarial_inputs_are_rejected(self):
        record = self.example()[0]
        for key, invalid in (
            ("seed", True), ("persona", "=SUM(A1)"), ("outcome", "ENGINE_WIN"),
            ("movesUsed", -1), ("score", float("nan")), ("score", float("inf")),
        ):
            wrong = dict(record); wrong[key] = invalid
            with self.subTest(field=key), self.assertRaises(ValueError):
                summarize_reference_records([wrong])
        with self.assertRaises(ValueError):
            summarize_reference_records([dict(record, unknownField=True)])
        with self.assertRaises(ValueError):
            summarize_reference_records([record] * 4097)
        self.assertIsNone(summarize_reference_records([])["medianObservedScore"])


if __name__ == "__main__":
    unittest.main()

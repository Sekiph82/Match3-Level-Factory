"""Read-only end-to-end reference-analysis tests; never issue Engine PASS."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from reference_analysis import analyze_ranked_output, main


def donor_fixture():
    p = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
    return leveldraft.loads_strict(p.read_text(encoding="utf-8"))


def record(draft):
    return {
        "draft": draft,
        "draftSha256": leveldraft.sha256(draft),
        "profileCompatibility": {"engineStatus": "BLOCKED_ENG_M24",
                                 "localPolicyStatus": "REJECTED_BY_BUILDER_POLICY",
                                 "draftMutationPerformed": False},
    }


class ReferenceAnalysisTests(unittest.TestCase):
    def sample(self):
        one = donor_fixture()
        two = copy.deepcopy(one)
        two["seed"] = 714
        two["levelId"] = "other.id"
        return {
            "resultStatus": "REFERENCE_ONLY_UNVERIFIED",
            "engineStatus": "BLOCKED_ENG_M24",
            "sourceRepository": "JohannesBuchner/ultragem",
            "sourceRevision": "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12",
            "seed": 712, "drafts": [record(one), record(two)],
        }

    def test_reference_pipeline_summary_is_deterministic_and_cannot_release(self):
        report = analyze_ranked_output(self.sample())
        self.assertEqual(report, analyze_ranked_output(self.sample()))
        self.assertEqual(report["candidateCount"], 2)
        self.assertEqual(len(report["structuralDiversity"]["accepted"]), 1)
        self.assertEqual(len(report["structuralDiversity"]["rejected"]), 1)
        self.assertFalse(report["releaseAuthorized"])
        self.assertEqual(report["engineStatus"], "BLOCKED_ENG_M24")
        self.assertTrue(report["staticFeatures"][0]["features"]["notDifficultyOrSolvability"])

    def test_bad_sha_or_fabricated_engine_certification_fails_closed(self):
        for field, bad_value in (("draftSha256", "f"*64), ("profileCompatibility", {}),
                                 ("draft", {"draftVersion": 2})):
            with self.subTest(field=field):
                sample = self.sample()
                sample["drafts"][0][field] = bad_value
                with self.assertRaises((ValueError, leveldraft.DraftError)):
                    analyze_ranked_output(sample)
        sample = self.sample()
        sample["resultStatus"] = "ENGINE_CERTIFIED"
        with self.assertRaises(ValueError):
            analyze_ranked_output(sample)

    def test_read_only_cli_never_mutates_original(self):
        sample = self.sample()
        with tempfile.TemporaryDirectory(prefix="lfx-analysis-") as folder:
            input_path = Path(folder) / "reference.json"
            payload = json.dumps(sample, ensure_ascii=False, sort_keys=True)
            input_path.write_text(payload, encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--input", str(input_path)]), 0)
            self.assertEqual(input_path.read_text(encoding="utf-8"), payload)
            result = json.loads(output.getvalue())
            self.assertFalse(result["releaseAuthorized"])
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--input", str(input_path), "--threshold", "nan"]), 2)


if __name__ == "__main__":
    unittest.main()

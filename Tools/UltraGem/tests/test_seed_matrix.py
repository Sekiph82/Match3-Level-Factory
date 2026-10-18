"""LFX-M07-003 strict donor reference runs and failure classification."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from factory_pipeline import ULTRAGEM_REVISION
from seed_matrix import sample_reference_seeds, _read_result


class SeedMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        cls.draft = leveldraft.loads_strict(p.read_text(encoding="utf-8"))

    def result(self, seed=712):
        draft = self.draft.copy()
        return json.dumps({
            "resultStatus": "REFERENCE_ONLY_UNVERIFIED", "engineStatus": "BLOCKED_ENG_M24",
            "sourceRevision": ULTRAGEM_REVISION, "seed": seed,
            "configuration": {"gameProfileId": "Coral_Rescue"},
            "drafts": [{"draft": draft, "draftSha256": leveldraft.sha256(draft),
                         "rankingStatus": "RANKED_REFERENCE_HEURISTIC",
                         "profileCompatibility": {"engineStatus": "BLOCKED_ENG_M24",
                                                  "localPolicyStatus": "REJECTED_BY_BUILDER_POLICY"}}],
        }, sort_keys=True)

    def test_seeded_result_integrity_is_reference_only(self):
        text = self.result()
        result = _read_result(text, 712, "Coral_Rescue")
        self.assertEqual(result["status"], "REFERENCE_OBSERVED")
        self.assertEqual(result["localPolicyRejectedDrafts"], 1)
        self.assertEqual(result["draftSha256"][0], leveldraft.sha256(self.draft))
        self.assertEqual(result, _read_result(text, 712, "Coral_Rescue"))

    def test_tampered_results_never_count_as_observed(self):
        for field, value in (("engineStatus", "ENGINE_CERTIFIED"),
                             ("sourceRevision", "fake"), ("seed", 713)):
            obj = json.loads(self.result()); obj[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                _read_result(json.dumps(obj), 712, "Coral_Rescue")
        obj = json.loads(self.result()); obj["drafts"][0]["draftSha256"] = "f"*64
        with self.assertRaises(ValueError):
            _read_result(json.dumps(obj), 712, "Coral_Rescue")

    @patch("seed_matrix.subprocess.run")
    def test_distribution_counts_unknown_fail_and_success(self, run):
        def emulate(command, **_):
            seed = int(command[command.index("--seed")+1])
            if seed == 1:
                return SimpleNamespace(returncode=0, stdout=self.result(seed), stderr="")
            if seed == 2:
                raise __import__("subprocess").TimeoutExpired("cmd", 2)
            return SimpleNamespace(returncode=3, stdout="", stderr="internal detail")
        run.side_effect = emulate
        report = sample_reference_seeds(seeds=[3, 1, 2])
        self.assertEqual(report["seeds"], [1, 2, 3])
        self.assertEqual(report["outcomeDistribution"]["REFERENCE_OBSERVED"], 1)
        self.assertEqual(report["outcomeDistribution"]["UNKNOWN_TIMEOUT_KILLED"], 1)
        self.assertEqual(report["outcomeDistribution"]["REFERENCE_FAIL_PROCESS_EXIT"], 1)
        self.assertFalse(report["allReferenceProcessesObserved"])
        self.assertIsNone(report["certifiedGameplaySuccessProbability"])
        self.assertFalse(report["releaseAuthorized"])
        self.assertNotIn("internal detail", json.dumps(report))

    def test_wrong_inputs_rejected_before_child_execution(self):
        for seeds in ([], [1, 1], [True], [-1], list(range(9))):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                sample_reference_seeds(seeds=seeds)
        with self.assertRaises(ValueError):
            sample_reference_seeds(seeds=[1], profile_id="fake")
        with self.assertRaises(ValueError):
            sample_reference_seeds(seeds=[1], timeout_seconds=60)
        with self.assertRaises(ValueError):
            sample_reference_seeds(seeds=[1], runs=20)

    def test_real_pinned_donor_one_seed_small_budget(self):
        result = sample_reference_seeds(seeds=[712], runs=1, max_moves=2, timeout_seconds=12)
        self.assertEqual(result["sourceRevision"], ULTRAGEM_REVISION)
        self.assertEqual(result["outcomeDistribution"]["REFERENCE_OBSERVED"], 1)
        self.assertIsNone(result["certifiedDifficulty"])
        self.assertFalse(result["releaseAuthorized"])

if __name__ == "__main__": unittest.main()

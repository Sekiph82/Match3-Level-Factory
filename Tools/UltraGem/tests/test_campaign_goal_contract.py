from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from campaign_goal_contract import (
    LOCAL_MOVE_BUDGET, LOCAL_SCORE_TARGET_COUNT, build_local_goal_proposal,
    diagnose_donor_goals, diagnose_local_sample_proposal, source_evidence,
    validate_local_goal_proposal,
)
from factory_pipeline import run_pipeline
from genlevels import SCORES_PREFERENCES
from profile_compatibility import PROFILE_IDS
from scoregames import STAT_NAMES


class CampaignGoalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = run_pipeline(rows=6, columns=6, colors=3, seed=73,
                                  candidate_count=1, runs=1, max_moves=2,
                                  profile_id=PROFILE_IDS[0], max_levels=1)
        cls.draft = cls.source["drafts"][0]["draft"]
        cls.sha = leveldraft.sha256(cls.draft)
        cls.diagnosis = diagnose_donor_goals(cls.draft["goals"])

    def build(self, *, draft=None, diagnosis=None):
        d = copy.deepcopy(draft or self.draft)
        diag = copy.deepcopy(diagnosis or diagnose_donor_goals(d["goals"]))
        return build_local_goal_proposal(
            source_draft=d, source_draft_sha256=leveldraft.sha256(d),
            source_record_path="candidates/Coral_Rescue/attempt-001-test.json",
            source_repository="JohannesBuchner/ultragem",
            source_revision="0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12",
            source_goal_diagnosis=diag, source_ranking_status="NOT_RANKED_BY_PINNED_HEURISTIC",
            project_root=PROJECT_ROOT)

    def test_donor_ranked_goal_vocabulary_is_exact_subset_of_observed_statistics(self):
        ranked = {name for group in SCORES_PREFERENCES for name in group}
        self.assertEqual(ranked, {"nunlocked", "combo_22", "combo_42", "combo_44",
                                  "combo_52", "combo_54", "combo_55", "nstripe",
                                  "nbomb", "nzapper", "score"})
        self.assertTrue(ranked.issubset(set(STAT_NAMES)))
        for goal_id in sorted(ranked):
            result = diagnose_donor_goals([{"goalId": "goal.primary",
                                            "targetId": f"ultragem.goal.{goal_id}",
                                            "targetCount": 17}])
            self.assertEqual(result["goals"][0]["status"], "SEMANTICS_VERIFIED_DONOR_ONLY")
            self.assertEqual(result["goals"][0]["localEquivalence"], "NOT_ESTABLISHED")

    def test_all_goal_diagnoses_include_hashes_for_donor_and_local_sources(self):
        evidence = source_evidence(PROJECT_ROOT)
        self.assertGreaterEqual(len(evidence), 10)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in evidence))
        self.assertIn("Tools/UltraGem/genlevels.py", {item["path"] for item in evidence})
        self.assertIn("Assets/Match3/Scripts/Match3.cs", {item["path"] for item in evidence})

    def test_unranked_mapper_placeholder_is_identifier_only(self):
        result = diagnose_donor_goals([{"goalId": "goal.primary", "targetId": "ultragem.score", "targetCount": 1}])
        self.assertEqual(result["goals"][0]["status"], "IDENTIFIER_ONLY")
        self.assertEqual(result["reasonCode"], "UNRANKED_MAPPER_PLACEHOLDER")
        self.assertTrue(result["proposalEligible"])

    def test_unknown_and_malicious_goal_ids_are_rejected(self):
        for target in ("ultragem.goal.evil", "sample.score;win=true", "../../sample.score"):
            result = diagnose_donor_goals([{"goalId": "goal.primary", "targetId": target, "targetCount": 1}])
            self.assertFalse(result["proposalEligible"], target)
            self.assertTrue(result["reasonCode"].startswith("GOAL_") or
                            result["reasonCode"] == "GOAL_TARGET_NOT_IN_PINNED_DONOR_CONTRACT")

    def test_non_integer_zero_and_boolean_target_counts_are_rejected(self):
        for count in (0, -1, True, 1.0, "1"):
            result = diagnose_donor_goals([{"goalId": "goal.primary", "targetId": "ultragem.goal.score", "targetCount": count}])
            self.assertEqual(result["goals"][0]["status"], "REJECTED_INVALID_TARGET_COUNT")
            self.assertFalse(result["proposalEligible"])

    def test_multiple_conflicting_source_goals_are_not_proposed(self):
        result = diagnose_donor_goals([
            {"goalId": "goal.primary", "targetId": "ultragem.goal.score", "targetCount": 500},
            {"goalId": "goal.secondary", "targetId": "ultragem.goal.nstripe", "targetCount": 4},
        ])
        self.assertEqual(result["status"], "REJECTED_MULTIPLE_SOURCE_GOALS")
        self.assertFalse(result["proposalEligible"])
        self.assertIsNone(self.build(diagnosis=result))

    def test_local_proposal_has_separate_source_to_derived_sha_and_preserves_source(self):
        source_before = leveldraft.dumps_canonical(self.draft)
        proposal = self.build()
        self.assertIsNotNone(proposal)
        self.assertEqual(leveldraft.dumps_canonical(self.draft), source_before)
        self.assertEqual(proposal["sourceDraftSha256"], self.sha)
        self.assertEqual(proposal["authoredLocalGoalProposalSha256"], leveldraft.sha256(proposal["draft"]))
        self.assertNotEqual(proposal["sourceDraftSha256"], proposal["authoredLocalGoalProposalSha256"])
        self.assertEqual(proposal["originalDonorGoals"], self.draft["goals"])
        self.assertEqual(proposal["draft"]["goals"], [{"goalId": "goal.primary", "targetId": "sample.score", "targetCount": 500}])
        validate_local_goal_proposal(proposal, project_root=PROJECT_ROOT)

    def test_proposal_does_not_inherit_donor_difficulty_target_count_or_move_budget_or_win(self):
        proposal = self.build()
        self.assertEqual(proposal["draft"]["moveBudget"], LOCAL_MOVE_BUDGET)
        self.assertEqual(proposal["draft"]["difficultyLabel"], "difficulty.unrated")
        self.assertEqual(proposal["authoring"]["targetCount"], LOCAL_SCORE_TARGET_COUNT)
        self.assertEqual(proposal["authoring"]["donorDifficultyHypothesisInherited"], False)
        self.assertEqual(proposal["authoring"]["donorTargetCountInherited"], False)
        self.assertEqual(proposal["authoring"]["donorMoveBudgetInherited"], False)
        self.assertEqual(proposal["authoring"]["winClaim"], False)
        self.assertNotIn("referenceDifficultyHypothesis", proposal)
        self.assertNotIn("difficultyHypothesis", proposal)

    def test_altered_proposal_goal_or_authority_receipt_is_rejected(self):
        for mutation in ("goal", "difficulty", "flag", "source"):
            proposal = self.build()
            if mutation == "goal":
                proposal["draft"]["goals"][0]["targetCount"] = 999
            elif mutation == "difficulty":
                proposal["draft"]["moveBudget"] = 11
            elif mutation == "flag":
                proposal["authoring"]["winClaim"] = True
            else:
                proposal["sourceDraftSha256"] = "not-a-sha"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_local_goal_proposal(proposal, project_root=PROJECT_ROOT)

    def test_wrong_profile_proposal_is_rejected_by_strict_leveldraft_schema(self):
        wrong = copy.deepcopy(self.draft)
        wrong["gameProfileId"] = "Not_A_Game"
        with self.assertRaises(ValueError):
            self.build(draft=wrong)

    def test_local_sample_goal_contract_is_provable_but_donor_board_fails_closed(self):
        proposal = self.build()
        diagnostics = diagnose_local_sample_proposal(proposal["draft"], PROJECT_ROOT)
        self.assertEqual(diagnostics["status"], "REJECTED_LOCAL_SAMPLE_COMPATIBILITY")
        codes = {item["code"] for item in diagnostics["findings"]}
        self.assertTrue(codes.intersection({"SAMPLE_GEM_BINDING_REQUIRED", "SAMPLE_CELL_MECHANIC_UNSUPPORTED"}))
        self.assertEqual(diagnostics["engineStatus"], "BLOCKED_ENG_M24")

    def test_mixed_none_and_string_content_diagnostics_are_deterministic(self):
        draft = copy.deepcopy(self.draft)
        cell = next(item for item in draft["cells"] if item["active"])
        cell.update(contentId=None, obstacleId="sample.glass", obstacleDurability=1,
                    locked=False, lockDurability=0, specialId=None)
        draft["goals"] = [{"goalId": "goal.primary", "targetId": "sample.score", "targetCount": 500}]
        first = diagnose_local_sample_proposal(draft, PROJECT_ROOT)
        second = diagnose_local_sample_proposal(draft, PROJECT_ROOT)
        self.assertEqual(first, second)
        finding = next(item for item in first["findings"] if item["code"] == "SAMPLE_GEM_BINDING_REQUIRED")
        self.assertIn(None, finding["sourceValues"])
        self.assertTrue(any(isinstance(item, str) for item in finding["sourceValues"]))

    def test_studio_palette_source_change_blocks_local_contract_interpretation(self):
        draft = copy.deepcopy(self.draft)
        for cell in draft["cells"]:
            if cell["active"]:
                cell.update(contentId="Blue", locked=False, lockDurability=0, specialId=None,
                            obstacleId=None, obstacleDurability=0)
        draft["goals"] = [{"goalId": "goal.primary", "targetId": "sample.score", "targetCount": 500}]
        from unittest.mock import patch
        with patch("campaign_goal_contract._STUDIO_GEMS", {"Changed"}):
            self.assertEqual(diagnose_local_sample_proposal(draft, PROJECT_ROOT)["status"],
                             "REJECTED_LOCAL_SAMPLE_COMPATIBILITY")


if __name__ == "__main__":
    unittest.main()

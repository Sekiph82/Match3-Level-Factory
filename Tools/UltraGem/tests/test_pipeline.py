from __future__ import annotations

import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from factory_pipeline import main as pipeline_main, run_pipeline, serialize_result
from genlevels import rank_levels
from scoregames import STAT_NAMES, create_scenario, evaluate_candidate, scoring_function


class UltraGemCompatibilityTests(unittest.TestCase):
    def test_seeded_candidate_board_is_repeatable(self):
        left, _ = create_scenario(8, 8, 3, 712)
        right, _ = create_scenario(8, 8, 3, 712)
        self.assertEqual(left, right)

    def test_non_square_scenario_uses_column_range(self):
        board, _ = create_scenario(7, 9, 4, 91)
        self.assertEqual(board.shape, (7, 9))

    def test_policy_simulation_is_bounded_and_seeded(self):
        first = evaluate_candidate(6, 6, 3, 22, runs=1, max_moves=2)
        second = evaluate_candidate(6, 6, 3, 22, runs=1, max_moves=2)
        self.assertEqual(serialize_result(first), serialize_result(second))
        self.assertNotIn("durationSeconds", first)
        for name in ("worst", "random", "best", "smart"):
            self.assertEqual(first["statistics"][name]["runSeeds"], second["statistics"][name]["runSeeds"])
            self.assertLessEqual(len(first["statistics"][name]["steps"][0]), 2)

    def test_event_scoring_preserves_donor_metric_order(self):
        self.assertEqual(
            scoring_function([("activated", 2), ("unlocked", 3), ("destroyed", 4), ("combined", 22)]),
            [24, 4, 3, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        )

    def test_pinned_difficulty_heuristic_can_rank_a_candidate(self):
        metric_count = len(STAT_NAMES)
        goal_index = STAT_NAMES.index("score")
        best = [[0] * metric_count for _ in range(20)]
        random = [[0] * metric_count for _ in range(20)]
        smart = [[0] * metric_count for _ in range(20)]
        for step in range(20):
            best[step][goal_index] = step + 1
            random[step][goal_index] = step + 3
            smart[step][goal_index] = step + 5
        candidate = {
            "seed": 41, "candidateIndex": 0, "colors": 4,
            "initialBoard": {"rows": 8, "columns": 8, "cells": []},
            "statistics": {name: {"steps": [values, values]} for name, values in
                           (("best", best), ("random", random), ("smart", smart))},
        }
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            levels = rank_levels([candidate], seed=41, max_levels=1)
        self.assertEqual(len(levels), 1)
        self.assertEqual(levels[0]["goalId"], "score")
        self.assertGreater(levels[0]["difficultyHypothesis"], 0)


class LevelDraftTests(unittest.TestCase):
    def candidate(self):
        return {
            "seed": 55,
            "initialBoard": {
                "rows": 2, "columns": 2,
                "cells": [
                    {"row": 0, "column": 0, "type": -1, "color": 0, "status": 0},
                    {"row": 0, "column": 1, "type": 0, "color": 0, "status": 2},
                    {"row": 1, "column": 0, "type": 1, "color": 1, "status": 1},
                    {"row": 1, "column": 1, "type": 4, "color": 2, "status": 0},
                ],
            },
        }

    def test_ultragem_mapping_preserves_row_column_holes_locks_and_specials(self):
        draft = leveldraft.from_ultragem(self.candidate())
        self.assertEqual((draft["width"], draft["height"]), (2, 2))
        self.assertEqual(draft["activeMask"], [False, True, True, True])
        self.assertEqual(draft["cells"][0]["active"], False)
        locked = next(cell for cell in draft["cells"] if cell["row"] == 0 and cell["column"] == 1)
        self.assertEqual((locked["obstacleId"], locked["obstacleDurability"]), ("ultragem.double_lock", 2))
        colored_lock = next(cell for cell in draft["cells"] if cell["row"] == 1 and cell["column"] == 0)
        self.assertEqual((colored_lock["contentId"], colored_lock["lockDurability"]), ("ultragem.color.1", 1))
        special = next(cell for cell in draft["cells"] if cell["row"] == 1 and cell["column"] == 1)
        self.assertEqual(special["specialId"], "ultragem.bomb")

    def test_canonical_json_roundtrip_and_hash_are_stable(self):
        draft = leveldraft.from_ultragem(self.candidate())
        encoded = leveldraft.dumps_canonical(draft)
        decoded = leveldraft.loads_strict(encoded)
        self.assertEqual(encoded, leveldraft.dumps_canonical(decoded))
        self.assertEqual(leveldraft.sha256(draft), leveldraft.sha256(decoded))

    def test_shared_csharp_python_unicode_golden_fixture(self):
        fixture = ROOT.parents[1] / "Assets" / "Match3Factory" / "Tests" / "Fixtures" / "leveldraft_v1_unicode.json"
        encoded = fixture.read_text(encoding="utf-8").lstrip("\ufeff").strip()
        draft = leveldraft.loads_strict(encoded)
        self.assertEqual(leveldraft.dumps_canonical(draft), encoded)
        self.assertEqual(leveldraft.sha256(draft), "60943fb8cc6a9941803f66e9785b12ccaa70af12648042e05ed594868af209a4")

    def test_duplicate_json_keys_are_rejected(self):
        draft = leveldraft.from_ultragem(self.candidate())
        encoded = leveldraft.dumps_canonical(draft)
        with self.assertRaisesRegex(leveldraft.DraftError, "duplicate JSON key"):
            leveldraft.loads_strict(encoded[:-1] + ',"seed":1}')

    def test_unknown_profile_unknown_fields_and_oversized_board_are_rejected(self):
        draft = leveldraft.from_ultragem(self.candidate())
        invalid = copy.deepcopy(draft)
        invalid["gameProfileId"] = "Other_Game"
        with self.assertRaisesRegex(leveldraft.DraftError, "unknown gameProfileId"):
            leveldraft.validate(invalid)
        invalid = copy.deepcopy(draft)
        invalid["unrecognized"] = True
        with self.assertRaisesRegex(leveldraft.DraftError, "unknown draft fields"):
            leveldraft.validate(invalid)
        invalid = copy.deepcopy(draft)
        invalid["width"] = 33
        with self.assertRaisesRegex(leveldraft.DraftError, "width must be"):
            leveldraft.validate(invalid)
        invalid = copy.deepcopy(draft)
        invalid["releaseChannel"] = "production"
        with self.assertRaisesRegex(leveldraft.DraftError, "releaseChannel"):
            leveldraft.validate(invalid)
        invalid = copy.deepcopy(draft)
        invalid["minEngineVersion"] = "1.0"
        with self.assertRaisesRegex(leveldraft.DraftError, "Engine version constraints"):
            leveldraft.validate(invalid)

    def test_cli_rejects_parent_traversal_before_running_pipeline(self):
        stderr = io.StringIO()
        with patch("factory_pipeline.run_pipeline", side_effect=AssertionError("pipeline must not run")):
            with contextlib.redirect_stderr(stderr):
                result = pipeline_main(["--output", "../outside.json"])
        self.assertEqual(result, 2)
        self.assertIn("parent traversal", stderr.getvalue())

    def test_pipeline_reports_engine_gate_and_is_deterministic(self):
        first = run_pipeline(rows=6, columns=6, colors=3, seed=28, candidate_count=1,
                             runs=1, max_moves=2,
                             profile_id="Coral_Rescue", max_levels=2)
        second = run_pipeline(rows=6, columns=6, colors=3, seed=28, candidate_count=1,
                              runs=1, max_moves=2,
                              profile_id="Coral_Rescue", max_levels=2)
        self.assertEqual(first["resultStatus"], "REFERENCE_ONLY_UNVERIFIED")
        self.assertEqual(first["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(serialize_result(first), serialize_result(second))
        self.assertNotIn("elapsedSeconds", first)
        self.assertEqual(first["candidateCountCompleted"], 1)

    def test_cli_refuses_to_overwrite_existing_output_without_flag(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd() / "Logs") as temp_dir:
            output = Path(temp_dir) / "owner-data.json"
            original = b"keep this exact file\n"
            output.write_bytes(original)
            stderr = io.StringIO()
            with patch("factory_pipeline.run_pipeline", return_value={"resultStatus": "test"}):
                with contextlib.redirect_stderr(stderr):
                    result = pipeline_main(["--output", str(output.relative_to(Path.cwd()))])
            self.assertEqual(result, 2)
            self.assertIn("File exists", stderr.getvalue())
            self.assertEqual(output.read_bytes(), original)

    def test_cli_overwrite_requires_and_honors_explicit_flag(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd() / "Logs") as temp_dir:
            output = Path(temp_dir) / "result.json"
            output.write_text("old", encoding="utf-8")
            with patch("factory_pipeline.run_pipeline", return_value={"resultStatus": "new"}):
                result = pipeline_main(["--output", str(output.relative_to(Path.cwd())), "--overwrite"])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"resultStatus": "new"})

    def test_pipeline_emits_editable_unranked_draft_when_heuristic_rejects(self):
        result = run_pipeline(rows=6, columns=6, colors=3, seed=17, candidate_count=1,
                              runs=1, max_moves=10,
                              profile_id="Coral_Rescue", max_levels=5)
        self.assertEqual(result["rankedLevels"], [])
        self.assertEqual(result["unrankedDraftCount"], 1)
        self.assertEqual(result["drafts"][0]["rankingStatus"], "NOT_RANKED_BY_PINNED_HEURISTIC")
        self.assertIsNone(result["drafts"][0]["difficultyHypothesis"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

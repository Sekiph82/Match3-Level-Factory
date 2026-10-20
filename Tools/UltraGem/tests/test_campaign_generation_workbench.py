from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import leveldraft
from campaign_generation_workbench import (
    MAX_BATCH_WORK_UNITS, WorkbenchError, run_campaign_batch, validate_config,
)
from factory_pipeline import ULTRAGEM_REVISION, run_pipeline
from profile_compatibility import PROFILE_IDS


def config(*, profiles=None, attempts=1, runs=1, moves=2):
    return {
        "profiles": list(profiles or [PROFILE_IDS[0]]),
        "attemptsPerProfile": attempts, "seedStart": 500,
        "rows": 6, "columns": 6, "colors": 3,
        "runs": runs, "maxMoves": moves,
        "candidateTimeoutSeconds": 10, "nearDuplicateThreshold": 0.95,
    }


class CampaignGenerationWorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = run_pipeline(rows=6, columns=6, colors=3, seed=1,
                                  candidate_count=1, runs=1, max_moves=1,
                                  profile_id=PROFILE_IDS[0], max_levels=1)
        cls.template = cls.source["drafts"][0]["draft"]

    def fake_runner(self, **kwargs):
        draft = copy.deepcopy(self.template)
        draft["gameProfileId"] = kwargs["profile_id"]
        draft["seed"] = kwargs["seed"]
        draft["levelId"] = f"level.seed-{kwargs['seed']}"
        return {
            "resultStatus": "REFERENCE_ONLY_UNVERIFIED",
            "sourceRevision": ULTRAGEM_REVISION,
            "sourceRepository": "JohannesBuchner/ultragem",
            "seed": kwargs["seed"],
            "configuration": {"gameProfileId": kwargs["profile_id"]},
            "drafts": [{"draft": draft, "rankingStatus": "NOT_RANKED_BY_PINNED_HEURISTIC",
                        "difficultyHypothesis": None}],
            "referenceStatistics": [{"seed": kwargs["seed"], "statistics": {
                "worst": {"runSeeds": [kwargs["seed"]], "movesUsed": [2],
                          "shuffles": [0], "outcomes": ["MOVE_LIMIT"],
                          "steps": [[[3, 0], [7, 0]]]},
            }}],
        }

    def run_fake(self, folder, cfg, runner=None, **kwargs):
        Path(folder).mkdir()
        return run_campaign_batch(config=cfg, output_dir=folder,
                                  pipeline_runner=runner or self.fake_runner, **kwargs)

    def test_five_profiles_generate_separate_namespaces_and_keep_engine_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "five-profile-run"
            summary = self.run_fake(out, config(profiles=PROFILE_IDS))
            self.assertEqual(summary["sourceBackedCandidateOutputs"], 5)
            self.assertEqual(set(summary["profileResults"]), set(PROFILE_IDS))
            self.assertEqual(summary["engineQualifiedCampaignLevels"], 0)
            self.assertEqual(summary["engineStatus"], "BLOCKED_ENG_M24")
            self.assertTrue(all(item["profileId"] in PROFILE_IDS for item in summary["records"]))

    def test_goal_only_and_color_renaming_variants_are_not_unique(self):
        calls = 0

        def goal_only(**kwargs):
            nonlocal calls
            result = self.fake_runner(**kwargs)
            if calls:
                result["drafts"][0]["draft"]["goals"][0]["targetCount"] += 1
            calls += 1
            return result

        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "goal-only"
            summary = self.run_fake(out, config(attempts=2), runner=goal_only)
            self.assertEqual(summary["uniqueOwnerReviewCandidates"], 0)
            self.assertEqual(summary["records"][1]["triageStatus"], "REJECTED_NEAR_DUPLICATE")

        left = copy.deepcopy(self.template)
        right = copy.deepcopy(self.template)
        for cell in right["cells"]:
            if cell["contentId"] and cell["contentId"].startswith("ultragem.color."):
                color = int(cell["contentId"].rsplit(".", 1)[1])
                cell["contentId"] = f"ultragem.color.{(color + 1) % 3}"
        self.assertEqual(
            __import__("candidate_diversity").structural_fingerprint(left),
            __import__("candidate_diversity").structural_fingerprint(right),
        )

    def test_checkpoint_resume_and_record_hash_revalidation(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "resume-run"
            out.mkdir()
            cancel = out / "CANCEL.request"
            def stop_after_first(progress):
                if progress["completed"] == 1:
                    cancel.write_text("stop", encoding="utf-8")
            partial = run_campaign_batch(config=config(attempts=2), output_dir=out,
                                         cancel_file=cancel, pipeline_runner=self.fake_runner,
                                         progress_callback=stop_after_first)
            self.assertEqual(partial["resultStatus"], "CANCELLED")
            cancel.unlink()
            resumed = run_campaign_batch(config=config(attempts=2), output_dir=out,
                                         resume=True, pipeline_runner=self.fake_runner)
            self.assertEqual(resumed["sourceBackedCandidateOutputs"], 2)
            candidate = out / resumed["records"][0]["recordPath"]
            candidate.write_text(candidate.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesRegex(WorkbenchError, "record SHA-256"):
                run_campaign_batch(config=config(attempts=2), output_dir=out,
                                   resume=True, pipeline_runner=self.fake_runner)

    def test_resume_adopts_identical_candidate_written_before_checkpoint_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "orphan-recovery"
            out.mkdir()
            with patch("campaign_generation_workbench._save_checkpoint",
                       side_effect=RuntimeError("simulated interruption after record write")):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    run_campaign_batch(config=config(), output_dir=out,
                                      pipeline_runner=self.fake_runner)
            self.assertEqual(len(list((out / "candidates").rglob("*.json"))), 1)
            resumed = run_campaign_batch(config=config(), output_dir=out,
                                         resume=True, pipeline_runner=self.fake_runner)
            self.assertEqual(resumed["sourceBackedCandidateOutputs"], 1)
            self.assertEqual(len(resumed["records"]), 1)

    def test_preexisting_run_data_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "existing-run"
            out.mkdir()
            existing = out / "owner.txt"
            existing.write_text("owner", encoding="utf-8")
            with self.assertRaisesRegex(WorkbenchError, "must be empty"):
                run_campaign_batch(config=config(), output_dir=out, pipeline_runner=self.fake_runner)
            self.assertEqual(existing.read_text(encoding="utf-8"), "owner")

    def test_invalid_profiles_bounds_and_total_work_fail_closed(self):
        with self.assertRaises(WorkbenchError):
            validate_config(config(profiles=["invented-profile"]))
        invalid = config(attempts=101)
        with self.assertRaises(WorkbenchError):
            validate_config(invalid)
        too_large = config(profiles=PROFILE_IDS, attempts=100, runs=8, moves=40)
        self.assertGreater(5 * 100 * 8 * 40 * 4, MAX_BATCH_WORK_UNITS)
        with self.assertRaisesRegex(WorkbenchError, "total work budget"):
            validate_config(too_large)

    def test_bad_or_stale_checkpoint_is_refused_before_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "stale-run"
            out.mkdir()
            run_campaign_batch(config=config(), output_dir=out,
                               cancel_file=out / "CANCEL.request",
                               pipeline_runner=self.fake_runner)
            checkpoint = out / "checkpoint.json"
            checkpoint.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(WorkbenchError, "SHA-256"):
                run_campaign_batch(config=config(), output_dir=out, resume=True,
                                   pipeline_runner=self.fake_runner)

    def test_cli_rejects_path_traversal_and_existing_directory(self):
        from campaign_generation_workbench import _resolve_output
        root = Path.cwd()
        for unsafe in ("../outside", "Artifacts/../outside", "C:/outside"):
            with self.assertRaises(WorkbenchError):
                _resolve_output(root, unsafe)

    def test_profile_compatibility_rejection_is_explicit_and_not_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "compat-run"
            summary = self.run_fake(out, config())
            self.assertEqual(summary["generationAttempts"], 1)
            self.assertEqual(summary["generatedReferenceCandidates"], 0)
            self.assertEqual(summary["uniqueOwnerReviewCandidates"], 0)
            self.assertEqual(summary["records"][0]["triageStatus"], "REJECTED_PROFILE_COMPATIBILITY")
            body = json.loads((out / summary["records"][0]["recordPath"]).read_text(encoding="utf-8"))
            self.assertTrue(body["sourceGenerated"])
            self.assertEqual(body["engineStatus"], "BLOCKED_ENG_M24")
            self.assertGreater(body["coverage"]["activeCellCount"], 0)
            self.assertIn("scoreObservations", body["referenceStatistics"][0]["policies"]["worst"])
            leveldraft.validate(body["draft"])

    def test_progress_callback_reports_start_each_attempt_and_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "progress-run"
            out.mkdir()
            progress = []
            run_campaign_batch(config=config(), output_dir=out,
                               pipeline_runner=self.fake_runner,
                               progress_callback=progress.append)
            self.assertEqual(progress[0]["completed"], 0)
            self.assertEqual(progress[-1]["status"], "COMPLETED")
            self.assertEqual(progress[-1]["completed"], 1)

    def test_prestart_cancel_marker_in_editor_created_run_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "cancel-before-first-run"
            out.mkdir()
            marker = out / "CANCEL.request"
            marker.write_text("stop", encoding="utf-8")
            progress = []
            def must_not_run(**kwargs):
                raise AssertionError("cancel must be honored before launching donor worker")
            summary = run_campaign_batch(config=config(), output_dir=out,
                                         cancel_file=marker, pipeline_runner=must_not_run,
                                         progress_callback=progress.append)
            self.assertEqual(summary["resultStatus"], "CANCELLED")
            self.assertEqual(summary["generationAttempts"], 0)
            self.assertEqual(progress[-1]["status"], "CANCELLED")

    def test_resume_consumes_cancel_signal_without_deleting_its_record(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "resume-after-ui-cancel"
            out.mkdir()
            marker = out / "CANCEL.request"
            marker.write_text("stop", encoding="utf-8")
            partial = run_campaign_batch(config=config(), output_dir=out,
                                         pipeline_runner=self.fake_runner)
            self.assertEqual(partial["resultStatus"], "CANCELLED")
            resumed = run_campaign_batch(config=config(), output_dir=out,
                                         resume=True, pipeline_runner=self.fake_runner)
            self.assertEqual(resumed["sourceBackedCandidateOutputs"], 1)
            self.assertFalse(marker.exists())
            self.assertEqual(len(list(out.glob("CANCEL.request.consumed-*"))), 1)

    def test_cross_batch_screening_exceeds_legacy_64_item_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "cross-batch-65"
            summary = self.run_fake(out, config(attempts=65))
            self.assertEqual(summary["sourceBackedCandidateOutputs"], 65)
            self.assertEqual(summary["uniqueOwnerReviewCandidates"], 0)
            self.assertEqual(summary["records"][64]["triageStatus"], "REJECTED_DUPLICATE")

    def test_manifest_is_deterministic_and_excludes_variable_timings(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "manifest-a"
            second = Path(temp) / "manifest-b"
            self.run_fake(first, config())
            self.run_fake(second, config())
            self.assertEqual((first / "sha256-manifest.json").read_bytes(),
                             (second / "sha256-manifest.json").read_bytes())
            manifest = json.loads((first / "sha256-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("run-metrics.json", {item["path"] for item in manifest["files"]})
            self.assertEqual(len(json.loads((first / "run-metrics.json").read_text(encoding="utf-8"))), 1)

    def test_timeout_result_is_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "timeout-run"
            out.mkdir()
            with patch("campaign_generation_workbench._run_pipeline_with_timeout",
                       side_effect=TimeoutError("donor candidate exceeded timeout")):
                summary = run_campaign_batch(config=config(), output_dir=out,
                                             pipeline_runner=None)
            self.assertEqual(summary["generationAttempts"], 1)
            self.assertEqual(summary["sourceBackedCandidateOutputs"], 0)
            self.assertEqual(summary["records"][0]["triageStatus"], "FAILED")
            self.assertIn("timeout", summary["records"][0]["triageReason"])

    def test_worker_subprocess_receives_hard_timeout(self):
        import subprocess
        from campaign_generation_workbench import _run_pipeline_with_timeout
        with patch("campaign_generation_workbench.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="worker", timeout=3)) as run:
            with self.assertRaises(TimeoutError):
                _run_pipeline_with_timeout(timeout_seconds=3, rows=6, columns=6, colors=3,
                                           seed=1, candidate_count=1, runs=1, max_moves=1,
                                           profile_id=PROFILE_IDS[0], max_levels=1)
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    def test_invalid_json_is_rejected_by_the_shared_strict_draft_parser(self):
        with self.assertRaises(leveldraft.DraftError):
            leveldraft.loads_strict('{"draftVersion":1,')

    def test_runtime_generator_code_is_editor_scoped_and_engine_remains_external(self):
        editor_file = ROOT.parent.parent / "Assets" / "Match3Factory" / "Editor" / "CampaignGenerationWorkbenchWindow.cs"
        assembly = editor_file.parent / "Match3Factory.Editor.asmdef"
        self.assertTrue(editor_file.is_file())
        self.assertEqual(json.loads(assembly.read_text(encoding="utf-8"))["includePlatforms"], ["Editor"])
        source = editor_file.read_text(encoding="utf-8")
        self.assertIn("campaign_generation_workbench.py", source)
        self.assertIn("progress.json", source)
        self.assertIn("Cancel after current candidate", source)
        self.assertIn("BLOCKED", source)
        self.assertNotIn("UnityEngine.Player", source)


if __name__ == "__main__":
    unittest.main()

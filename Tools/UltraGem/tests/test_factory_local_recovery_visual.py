from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import factory_local_authoring as authoring
import factory_local_preview as preview
import leveldraft
from profile_compatibility import PROFILE_IDS


class FactoryLocalRecoveryVisualTests(unittest.TestCase):
    def setUp(self):
        project = Path(__file__).resolve().parents[3]
        self.root = project / "Artifacts" / ".local-authoring-tests" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)

    def start(self, name="Artifacts/run", *, profiles=None, attempts=2, width=6, height=6, colors=3):
        return authoring.start_run(self.root, name, profiles or [PROFILE_IDS[0]],
                                   attempts_per_profile=attempts, seed_start=900,
                                   width=width, height=height, colors=colors)

    def test_cancel_before_first_candidate_is_durable_and_resumable(self):
        self.start()
        authoring.request_cancel(self.root / "Artifacts/run")
        cancelled = authoring.run_session(self.root, "Artifacts/run")
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(cancelled["records"], [])
        completed = authoring.run_session(self.root, "Artifacts/run", resume=True)
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(len(completed["records"]), 2)

    def test_mid_batch_cancel_resume_preserves_saved_candidate_bytes(self):
        self.start(attempts=3)
        run_dir = self.root / "Artifacts/run"
        def stop_after_first(progress):
            if progress["completed"] == 1:
                authoring.request_cancel(run_dir)
        stopped = authoring.run_session(self.root, "Artifacts/run", progress_callback=stop_after_first)
        self.assertEqual(stopped["status"], "CANCELLED")
        first = stopped["records"][0]
        first_bytes = (run_dir / first["path"]).read_bytes()
        resumed = authoring.run_session(self.root, "Artifacts/run", resume=True)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual((run_dir / first["path"]).read_bytes(), first_bytes)

    def test_equal_config_runs_have_identical_candidate_and_manifest_bytes(self):
        self.start("Artifacts/a", attempts=2)
        self.start("Artifacts/b", attempts=2)
        a = authoring.run_session(self.root, "Artifacts/a")
        b = authoring.run_session(self.root, "Artifacts/b")
        self.assertEqual([r["rawSha256"] for r in a["records"]], [r["rawSha256"] for r in b["records"]])
        ma = json.loads((self.root / "Artifacts/a/manifest.json").read_text())
        mb = json.loads((self.root / "Artifacts/b/manifest.json").read_text())
        self.assertEqual(ma, mb)

    def test_crash_after_artifact_recovers_only_exact_deterministic_orphan(self):
        self.start()
        with self.assertRaisesRegex(RuntimeError, "injected crash"):
            authoring.run_session(self.root, "Artifacts/run", crash_after_artifact=True)
        resumed = authoring.run_session(self.root, "Artifacts/run", resume=True)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(resumed["events"][0]["event"], "CANDIDATE_RECOVERED")

    def test_corrupt_orphan_checkpoint_config_schema_and_extra_files_fail_closed(self):
        self.start("Artifacts/orphan")
        with self.assertRaises(RuntimeError):
            authoring.run_session(self.root, "Artifacts/orphan", crash_after_artifact=True)
        artifact = next((self.root / "Artifacts/orphan/drafts").rglob("*.json"))
        artifact.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "orphan bytes"):
            authoring.run_session(self.root, "Artifacts/orphan", resume=True)

        self.start("Artifacts/checkpoint")
        checkpoint_path = self.root / "Artifacts/checkpoint/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["configuration"]["seedStart"] += 1
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            authoring.run_session(self.root, "Artifacts/checkpoint")

        self.start("Artifacts/extra")
        (self.root / "Artifacts/extra/unexpected.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "unexpected file"):
            authoring.run_session(self.root, "Artifacts/extra")

    def test_completed_candidate_manifest_and_changed_config_are_revalidated_on_resume(self):
        self.start("Artifacts/candidate", attempts=1)
        completed = authoring.run_session(self.root, "Artifacts/candidate")
        record = completed["records"][0]
        draft_path = self.root / "Artifacts/candidate" / record["path"]
        draft_path.write_bytes(draft_path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "raw file hash"):
            authoring.run_session(self.root, "Artifacts/candidate", resume=True)

        self.start("Artifacts/manifest", attempts=1)
        authoring.run_session(self.root, "Artifacts/manifest")
        manifest_path = self.root / "Artifacts/manifest/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["entries"][0]["rawSha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest does not match"):
            authoring.run_session(self.root, "Artifacts/manifest", resume=True)

        self.start("Artifacts/config", attempts=1)
        cp_path = self.root / "Artifacts/config/checkpoint.json"
        cp = json.loads(cp_path.read_text())
        cp["configuration"]["seedStart"] += 1
        cp["configurationSha256"] = hashlib.sha256(authoring._json_bytes(cp["configuration"])).hexdigest()
        cp["checkpointSha256"] = authoring._seal(cp)["checkpointSha256"]
        cp_path.write_text(json.dumps(cp), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "run configuration"):
            authoring.run_session(self.root, "Artifacts/config")

    def test_stale_source_partial_path_traversal_and_symlink_are_rejected(self):
        with self.assertRaises(ValueError):
            self.start("../outside")
        self.start("Artifacts/run")
        checkpoint_path = self.root / "Artifacts/run/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["sourceRevision"] = "stale"
        body = dict(checkpoint); body.pop("checkpointSha256", None)
        checkpoint["checkpointSha256"] = hashlib.sha256(authoring._json_bytes(body)).hexdigest()
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale source"):
            authoring.run_session(self.root, "Artifacts/run")

        self.start("Artifacts/partial")
        (self.root / "Artifacts/partial/checkpoint.json.partial").write_text("partial")
        with self.assertRaisesRegex(ValueError, "partial artifact"):
            authoring.run_session(self.root, "Artifacts/partial")

        outside = self.root / "outside-target"
        outside.mkdir()
        link = self.root / "Artifacts" / "link"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink creation is not enabled in this environment")
        with self.assertRaisesRegex(ValueError, "symlink"):
            authoring.start_run(self.root, "Artifacts/link/child", [PROFILE_IDS[0]],
                                attempts_per_profile=1, seed_start=1)

    def test_rejects_unbounded_batch_wrong_profile_and_non_project_location(self):
        with self.assertRaises((ValueError, FileExistsError)):
            self.start(".")
        with self.assertRaises(ValueError):
            authoring.start_run(self.root, "Artifacts/x", ["NoSuchGame"], attempts_per_profile=1, seed_start=1)
        with self.assertRaises(ValueError):
            authoring.start_run(self.root, "Artifacts/y", list(PROFILE_IDS), attempts_per_profile=11, seed_start=1)

    def test_verified_png_is_deterministic_and_tampered_source_hash_is_rejected(self):
        self.start("Artifacts/run", profiles=[PROFILE_IDS[0]], attempts=1)
        result = authoring.run_session(self.root, "Artifacts/run")
        record = result["records"][0]
        source = self.root / "Artifacts/run" / record["path"]
        first = preview.render_verified_draft(source, record["draftSha256"], self.root / "one.png")
        second = preview.render_verified_draft(source, record["draftSha256"], self.root / "two.png")
        self.assertEqual(first["pngSha256"], second["pngSha256"])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            preview.render_verified_draft(source, "0" * 64, self.root / "bad.png")
        self.assertFalse((self.root / "bad.png").exists())

    def test_invalid_schema_and_unsupported_profile_colors_fail_before_png(self):
        src = self.root / "invalid.json"
        out = self.root / "out.png"
        src.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            preview.render_verified_draft(src, "0" * 64, out)
        self.assertFalse(out.exists())

    def test_five_profiles_two_real_configs_render_ten_boards_and_contact_sheet(self):
        self.start("Artifacts/run-6x6", profiles=list(PROFILE_IDS), attempts=1, width=6, height=6, colors=3)
        self.start("Artifacts/run-8x8", profiles=list(PROFILE_IDS), attempts=1, width=8, height=8, colors=4)
        first = authoring.run_session(self.root, "Artifacts/run-6x6")
        second = authoring.run_session(self.root, "Artifacts/run-8x8")
        self.assertEqual(len(first["records"]) + len(second["records"]), 10)
        visual = preview.build_visual_evidence([self.root / "Artifacts/run-6x6", self.root / "Artifacts/run-8x8"],
                                               self.root / "Artifacts/visual")
        self.assertEqual(len(visual["images"]), 10)
        self.assertEqual({entry["gameProfileId"] for entry in visual["images"]}, set(PROFILE_IDS))
        self.assertEqual({entry["grid"] for entry in visual["images"]}, {"6x6", "8x8"})
        self.assertTrue(all(entry["pngBytes"] < preview.MAX_PNG_BYTES for entry in visual["images"]))
        contact = self.root / "Artifacts/visual/contact-sheet.png"
        self.assertTrue(contact.is_file())
        self.assertEqual(visual["engineQualifiedCampaignLevels"], 0)
        self.assertEqual(visual["contactSheet"]["imageCount"], 10)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
import unittest
import ctypes
from unittest import mock
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
        self.start("Artifacts/uninterrupted", attempts=3)
        authoring.run_session(self.root, "Artifacts/uninterrupted")
        resumed_manifest = json.loads((run_dir / "manifest.json").read_text())
        uninterrupted_manifest = json.loads((self.root / "Artifacts/uninterrupted/manifest.json").read_text())
        self.assertEqual(resumed_manifest, uninterrupted_manifest)

    @unittest.skipUnless(os.name == "nt", "WinError 5/32 retry contract is Windows-specific")
    def test_atomic_replace_retries_transient_winerror_5_and_32(self):
        for winerror in (5, 32):
            with self.subTest(winerror=winerror):
                target = self.root / f"atomic-{winerror}.json"
                target.write_bytes(b"old bytes")
                original_replace = authoring.os.replace
                calls = 0

                def fail_twice_then_replace(source, destination):
                    nonlocal calls
                    calls += 1
                    if calls <= 2:
                        raise ctypes.WinError(winerror)
                    return original_replace(source, destination)

                with mock.patch.object(authoring.os, "replace", side_effect=fail_twice_then_replace):
                    authoring._atomic_replace(target, b"new bytes")
                self.assertEqual(calls, 3)
                self.assertEqual(target.read_bytes(), b"new bytes")
                self.assertFalse(target.with_name(target.name + ".partial").exists())

    @unittest.skipUnless(os.name == "nt", "WinError 5 retry contract is Windows-specific")
    def test_atomic_replace_permanent_winerror_preserves_target_and_partial(self):
        target = self.root / "atomic-terminal.json"
        target.write_bytes(b"original checkpoint")
        original_replace = authoring.os.replace
        calls = 0

        def always_deny(source, destination):
            nonlocal calls
            calls += 1
            raise ctypes.WinError(5)

        with mock.patch.object(authoring.os, "replace", side_effect=always_deny):
            with self.assertRaises(PermissionError):
                authoring._atomic_replace(target, b"replacement checkpoint")
        self.assertEqual(calls, 5)
        self.assertEqual(target.read_bytes(), b"original checkpoint")
        self.assertEqual(target.with_name(target.name + ".partial").read_bytes(), b"replacement checkpoint")

    def test_interruption_before_candidate_write_resumes_without_losing_checkpoint(self):
        self.start("Artifacts/before-write", attempts=2)
        run_dir = self.root / "Artifacts/before-write"
        checkpoint_path = run_dir / "checkpoint.json"
        original_create = authoring._atomic_create

        def interrupt_candidate(path, data):
            if path.name == "attempt-01.json":
                raise RuntimeError("injected interruption before candidate write")
            return original_create(path, data)

        with mock.patch.object(authoring, "_atomic_create", side_effect=interrupt_candidate):
            with self.assertRaisesRegex(RuntimeError, "before candidate write"):
                authoring.run_session(self.root, "Artifacts/before-write")
        interrupted_checkpoint = checkpoint_path.read_bytes()
        self.assertEqual(json.loads(interrupted_checkpoint)["records"], [])
        self.assertEqual(list((run_dir / "drafts").rglob("*.json")), [])
        resumed = authoring.run_session(self.root, "Artifacts/before-write", resume=True)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(len(resumed["records"]), 2)

    def test_crash_after_candidate_file_before_checkpoint_is_recovered_and_byte_stable(self):
        self.start("Artifacts/crash-after-file", attempts=2)
        run_dir = self.root / "Artifacts/crash-after-file"
        checkpoint_path = run_dir / "checkpoint.json"
        checkpoint_at_crash_boundary = []
        original_create = authoring._atomic_create

        def capture_checkpoint_after_candidate_create(path, data):
            original_create(path, data)
            if path.name == "attempt-01.json":
                checkpoint_at_crash_boundary.append(checkpoint_path.read_bytes())

        with mock.patch.object(authoring, "_atomic_create", side_effect=capture_checkpoint_after_candidate_create):
            with self.assertRaisesRegex(RuntimeError, "injected crash"):
                authoring.run_session(self.root, "Artifacts/crash-after-file", crash_after_artifact=True)
        orphan = next((run_dir / "drafts").rglob("*.json"))
        orphan_before = orphan.read_bytes()
        self.assertEqual(len(checkpoint_at_crash_boundary), 1)
        self.assertEqual(checkpoint_path.read_bytes(), checkpoint_at_crash_boundary[0])
        resumed = authoring.run_session(self.root, "Artifacts/crash-after-file", resume=True)
        self.assertEqual(resumed["events"][0]["event"], "CANDIDATE_RECOVERED")
        self.assertEqual(orphan.read_bytes(), orphan_before)
        self.assertEqual(resumed["status"], "COMPLETED")

    def test_crash_between_checkpoint_and_manifest_recovers_one_verified_record(self):
        self.start("Artifacts/crash-between", attempts=2)
        run_dir = self.root / "Artifacts/crash-between"
        checkpoint_path = run_dir / "checkpoint.json"
        manifest_path = run_dir / "manifest.json"
        original_replace = authoring._atomic_replace
        manifest_updates = 0

        def fail_after_checkpoint_before_second_manifest(path, data):
            nonlocal manifest_updates
            if path.name == "manifest.json":
                manifest_updates += 1
                if manifest_updates == 2:
                    raise RuntimeError("injected crash after checkpoint before manifest")
            return original_replace(path, data)

        with mock.patch.object(authoring, "_atomic_replace", side_effect=fail_after_checkpoint_before_second_manifest):
            with self.assertRaisesRegex(RuntimeError, "before manifest"):
                authoring.run_session(self.root, "Artifacts/crash-between")
        checkpoint_after_crash = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(checkpoint_after_crash["records"]), 1)
        self.assertEqual(previous_manifest["entries"], [])
        first = checkpoint_after_crash["records"][0]
        first_path = run_dir / first["path"]
        first_bytes = first_path.read_bytes()

        resumed = authoring.run_session(self.root, "Artifacts/crash-between", resume=True)
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(first_path.read_bytes(), first_bytes)
        self.assertEqual(len(json.loads(manifest_path.read_text(encoding="utf-8"))["entries"]), 2)

    @unittest.skipUnless(os.name == "nt", "WinError 5 retry contract is Windows-specific")
    def test_checkpoint_replace_failure_preserves_checkpoint_and_does_not_write_candidate(self):
        self.start("Artifacts/checkpoint-replace-failure")
        run_dir = self.root / "Artifacts/checkpoint-replace-failure"
        checkpoint_path = run_dir / "checkpoint.json"
        checkpoint_before = checkpoint_path.read_bytes()
        original_replace = authoring.os.replace
        calls = 0

        def always_deny(source, destination):
            nonlocal calls
            calls += 1
            raise ctypes.WinError(5)

        with mock.patch.object(authoring.os, "replace", side_effect=always_deny):
            with self.assertRaises(PermissionError):
                authoring.run_session(self.root, "Artifacts/checkpoint-replace-failure")
        self.assertEqual(calls, 5)
        self.assertEqual(checkpoint_path.read_bytes(), checkpoint_before)
        self.assertEqual(list((run_dir / "drafts").rglob("*.json")), [])
        self.assertTrue(checkpoint_path.with_name("checkpoint.json.partial").is_file())

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

    def test_corrupt_orphan_is_rejected_without_changing_checkpoint_or_orphan(self):
        self.start("Artifacts/orphan")
        checkpoint_path = self.root / "Artifacts/orphan/checkpoint.json"
        with self.assertRaisesRegex(RuntimeError, "injected crash"):
            authoring.run_session(self.root, "Artifacts/orphan", crash_after_artifact=True)
        checkpoint_before = checkpoint_path.read_bytes()
        artifact = next((self.root / "Artifacts/orphan/drafts").rglob("*.json"))
        artifact.write_text("tampered", encoding="utf-8")
        orphan_before = artifact.read_bytes()
        with self.assertRaisesRegex(ValueError, "orphan bytes"):
            authoring.run_session(self.root, "Artifacts/orphan", resume=True)
        self.assertEqual(checkpoint_path.read_bytes(), checkpoint_before)
        self.assertEqual(artifact.read_bytes(), orphan_before)

    def test_checkpoint_hash_rejects_corrupt_checkpoint(self):
        self.start("Artifacts/checkpoint-hash")
        checkpoint_path = self.root / "Artifacts/checkpoint-hash/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["configuration"]["seedStart"] += 1
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            authoring.run_session(self.root, "Artifacts/checkpoint-hash")

    def test_checkpoint_rejects_foreign_profile(self):
        self.start("Artifacts/foreign-profile")
        checkpoint_path = self.root / "Artifacts/foreign-profile/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["configuration"]["profiles"] = ["Unknown_Title"]
        checkpoint["configurationSha256"] = authoring._sha(authoring._json_bytes(checkpoint["configuration"]))
        checkpoint = authoring._seal(checkpoint)
        checkpoint_path.write_bytes(authoring._json_bytes(checkpoint, pretty=True))
        with self.assertRaisesRegex(ValueError, "checkpoint configuration is invalid"):
            authoring.run_session(self.root, "Artifacts/foreign-profile")

    def test_checkpoint_rejects_foreign_seed_or_run_config_drift(self):
        self.start("Artifacts/foreign-seed")
        checkpoint_path = self.root / "Artifacts/foreign-seed/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["configuration"]["seedStart"] += 50_000
        checkpoint["configurationSha256"] = authoring._sha(authoring._json_bytes(checkpoint["configuration"]))
        checkpoint = authoring._seal(checkpoint)
        checkpoint_path.write_bytes(authoring._json_bytes(checkpoint, pretty=True))
        with self.assertRaisesRegex(ValueError, "persisted run configuration"):
            authoring.run_session(self.root, "Artifacts/foreign-seed")

    def test_unexpected_extra_file_is_rejected(self):
        self.start("Artifacts/extra")
        (self.root / "Artifacts/extra/unexpected.txt").write_text("extra", encoding="utf-8")
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

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.start("../outside")

    def test_absolute_run_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "project-relative"):
            authoring.start_run(self.root, str(self.root / "Artifacts/absolute"), [PROFILE_IDS[0]],
                                attempts_per_profile=1, seed_start=1)

    def test_stale_source_revision_is_rejected(self):
        self.start("Artifacts/run")
        checkpoint_path = self.root / "Artifacts/run/checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["sourceRevision"] = "stale"
        body = dict(checkpoint); body.pop("checkpointSha256", None)
        checkpoint["checkpointSha256"] = hashlib.sha256(authoring._json_bytes(body)).hexdigest()
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale source"):
            authoring.run_session(self.root, "Artifacts/run")

    def test_partial_artifact_is_rejected(self):
        self.start("Artifacts/partial")
        (self.root / "Artifacts/partial/checkpoint.json.partial").write_text("partial")
        with self.assertRaisesRegex(ValueError, "partial artifact"):
            authoring.run_session(self.root, "Artifacts/partial")

    def test_real_windows_symlink_directory_is_rejected(self):
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

    def test_injected_symlink_parent_boundary_fails_closed(self):
        link = self.root / "Artifacts" / "injected-parent"
        link.mkdir(parents=True)
        original = Path.is_symlink
        with mock.patch.object(Path, "is_symlink", autospec=True,
                               side_effect=lambda path: Path(path) == link or original(path)):
            with self.assertRaisesRegex(ValueError, "symlink"):
                authoring.start_run(self.root, "Artifacts/injected-parent/child", [PROFILE_IDS[0]],
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

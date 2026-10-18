from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evidence_archive import build_evidence_routing, verify_local_manifest


class EvidenceArchiveTests(unittest.TestCase):
    def test_deterministic_hashes_and_never_packaged_routing(self):
        sample = {"session/seed712.xml": b"<test-run passed='1'/>",
                  "tests/tiny.json": b'{"seed":712}'}
        data = [{"path": "session/seed712.xml", "kind": "RAW_NUNIT", "bytes": sample["session/seed712.xml"]},
                {"path": "tests/tiny.json", "kind": "SOURCE_FIXTURE", "bytes": sample["tests/tiny.json"]}]
        manifest = build_evidence_routing(data, source_commit_sha="a"*40)
        self.assertTrue(verify_local_manifest(manifest, sample))
        self.assertTrue(all(f["excludeFromPlayerAndAddressables"] for f in manifest["files"]))
        self.assertEqual(manifest["files"][0]["storageRoute"], "DRIVE_05_EVIDENCE")
        self.assertEqual(manifest["files"][1]["storageRoute"], "GITHUB_TRACKED_SOURCE")
        self.assertFalse(manifest["releaseAuthorized"])
        self.assertEqual(manifest, build_evidence_routing(list(reversed(data)), source_commit_sha="a"*40))

    def test_modified_bytes_and_malformed_paths_fail(self):
        m = build_evidence_routing([{"path": "raw/trace.xml", "kind": "RAW_NUNIT", "bytes": b"one"}], source_commit_sha="f"*40)
        self.assertFalse(verify_local_manifest(m, {"raw/trace.xml": b"two"}))
        self.assertFalse(verify_local_manifest(dict(m, releaseAuthorized=True), {"raw/trace.xml": b"one"}))
        for path in ("../private", "/tmp/file", "C:/secret", "x\\y", "a//b", "a/./b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_evidence_routing([{"path": path, "kind": "RAW_NUNIT", "bytes": b"x"}], source_commit_sha="f"*40)
        with self.assertRaises(ValueError):
            build_evidence_routing([{"path": "x", "kind": "RAW_NUNIT", "bytes": b"x"}]*2, source_commit_sha="f"*40)


if __name__ == "__main__":
    unittest.main()

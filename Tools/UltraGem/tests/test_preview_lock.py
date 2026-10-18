"""Thread contention cannot overwrite the in-memory accepted preview."""
from __future__ import annotations
import copy
import concurrent.futures
import sys
import threading
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from preview_pack import build_preview_pack
from preview_lock import LocalPreviewRevisionStore,StalePreviewRevision


class PreviewLockTests(unittest.TestCase):
    def base(self):
        p=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(p.read_text(encoding="utf-8"))

    def test_stale_write_fails_without_mutating_committed_revision(self):
        a=self.base()
        store=LocalPreviewRevisionStore(build_preview_pack([a]))
        state=store.snapshot()
        altered=copy.deepcopy(a);altered["seed"]+=1
        next_manifest=build_preview_pack([altered])
        r=store.compare_and_swap(expected_revision=state["revision"],
               expected_sha256=state["manifestSha256"],proposed_manifest=next_manifest)
        self.assertEqual(r["revision"],1)
        self.assertFalse(r["distributedLockAcquired"])
        self.assertFalse(r["remotePublishAuthorized"])
        with self.assertRaises(StalePreviewRevision):
            store.compare_and_swap(expected_revision=state["revision"],
                 expected_sha256=state["manifestSha256"],proposed_manifest=next_manifest)
        self.assertEqual(store.snapshot()["revision"],1)
        external=store.snapshot()
        external["manifest"]["groups"].clear()
        self.assertNotEqual(store.snapshot()["manifest"]["groups"],[])

    def test_competing_threads_only_one_writes(self):
        base=self.base()
        store=LocalPreviewRevisionStore(build_preview_pack([base]))
        s=store.snapshot()
        barrier=threading.Barrier(8)
        def competitor(index):
            changed=copy.deepcopy(base)
            changed["seed"]+=index+1
            candidate=build_preview_pack([changed])
            barrier.wait()
            try:
                store.compare_and_swap(expected_revision=s["revision"],
                                       expected_sha256=s["manifestSha256"],
                                       proposed_manifest=candidate)
                return True
            except StalePreviewRevision:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes=list(pool.map(competitor,range(8)))
        self.assertEqual(sum(outcomes),1)
        self.assertEqual(store.snapshot()["revision"],1)

    def test_production_and_forged_pack_rejected(self):
        store=LocalPreviewRevisionStore(build_preview_pack([self.base()]))
        snap=store.snapshot()
        bad=copy.deepcopy(snap["manifest"]);bad["publishAuthorized"]=True
        with self.assertRaises(ValueError):
            store.compare_and_swap(expected_revision=0,expected_sha256=snap["manifestSha256"],
                                  proposed_manifest=bad)
        self.assertEqual(store.snapshot()["revision"],0)

if __name__=="__main__":
    unittest.main()

from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from preview_pack import build_preview_pack
from preview_diff import diff_preview_manifests

class PreviewDiffTests(unittest.TestCase):
    def draft(self):
        p=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(p.read_text(encoding="utf-8"))
    def test_create_change_and_delete_never_publishes(self):
        a=self.draft()
        b=copy.deepcopy(a);b["levelId"]="other.id"
        old=build_preview_pack([a,b])
        newer=copy.deepcopy(a);newer["seed"]+=1
        c=copy.deepcopy(a);c["levelId"]="third.id"
        new=build_preview_pack([newer,c])
        result=diff_preview_manifests(old,new)
        self.assertEqual(len(result["updated"]),1)
        self.assertEqual(len(result["deleted"]),1)
        self.assertEqual(len(result["created"]),1)
        self.assertEqual(len(result["unchanged"]),0)
        self.assertFalse(result["publishAuthorized"])
        self.assertFalse(result["deleteRemoteObjectsAuthorized"])
        self.assertEqual(result,diff_preview_manifests(old,new))
    def test_wrong_channel_or_fabricated_engine_state_rejected(self):
        a=self.draft()
        previous=build_preview_pack([a])
        after=copy.deepcopy(previous)
        after["channel"]="production"
        with self.assertRaises(ValueError):
            diff_preview_manifests(previous,after)
        after=copy.deepcopy(previous)
        after["publishAuthorized"]=True
        with self.assertRaises(ValueError):
            diff_preview_manifests(previous,after)
        after=copy.deepcopy(previous)
        after["groups"][0]["levels"].append(copy.deepcopy(after["groups"][0]["levels"][0]))
        after["levelCount"]=2
        with self.assertRaises(ValueError):
            diff_preview_manifests(previous,after)

if __name__=="__main__": unittest.main()

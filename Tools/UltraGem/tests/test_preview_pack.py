from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import leveldraft
from preview_pack import build_preview_pack


class PreviewPackTests(unittest.TestCase):
    def draft(self):
        path = ROOT.parents[1] / "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        return leveldraft.loads_strict(path.read_text(encoding="utf-8"))

    def test_groups_five_game_drafts_without_game_art_or_runtime(self):
        original = self.draft()
        ids = ("Coral_Rescue","Garage_Legends","Dino_Islands","The_Fractured_Realms","Wonder_Pop")
        drafts=[]
        for i,game in enumerate(ids):
            item=copy.deepcopy(original)
            item["gameProfileId"]=game
            item["levelId"]="sample."+str(i)
            drafts.append(item)
        packed=build_preview_pack(drafts)
        self.assertEqual(packed["levelCount"],5)
        self.assertEqual(len(packed["groups"]),5)
        self.assertFalse(packed["publishAuthorized"])
        self.assertFalse(packed["signed"])
        self.assertFalse(packed["containsGameRuntimeOrArt"])
        self.assertEqual(packed["engineStatus"],"BLOCKED_ENG_M24")
        for group in packed["groups"]:
            self.assertEqual(len(group["levels"]),1)
            self.assertEqual(len(group["levels"][0]["draftSha256"]),64)
        self.assertEqual(packed, build_preview_pack(list(reversed(drafts))))

    def test_duplicate_identity_and_channel_guard(self):
        a=self.draft()
        with self.assertRaises(ValueError):
            build_preview_pack([a,a])
        with self.assertRaises(ValueError):
            build_preview_pack([a],channel="production")
        with self.assertRaises(ValueError):
            build_preview_pack([a],channel="staging")
        modified=copy.deepcopy(a)
        modified["engineSchemaVersion"]="fake-final"
        with self.assertRaises(leveldraft.DraftError):
            build_preview_pack([modified])
        with self.assertRaises(ValueError):
            build_preview_pack([])


if __name__=="__main__":
    unittest.main()

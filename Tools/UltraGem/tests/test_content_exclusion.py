from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from content_exclusion import validate_preview_file_inventory

class ContentExclusionTests(unittest.TestCase):
    def record(self,path="levels/coral_1.json",kind="LEVEL_JSON",rights="REFERENCE_ONLY"):
        return {"path":path,"sha256":"a"*64,"sizeBytes":100,"kind":kind,"rightsStatus":rights}
    def test_safe_preview_is_never_final_release(self):
        a=validate_preview_file_inventory([self.record(),self.record("media/owner_icon.png","MEDIA","OWNER_ORIGINAL")])
        self.assertEqual(len(a["acceptedForFurtherInspection"]),2)
        self.assertFalse(a["productionReleaseAuthorized"])
        self.assertFalse(a["runtimePackInspected"])
        self.assertEqual(a["engineStatus"],"BLOCKED_ENG_M24")
    def test_foreign_code_credentials_and_unlicensed_art_are_denied(self):
        cases=[
          self.record("Assets/Match3Factory/Core/Resolver.cs"),
          self.record("tests/fixture.json"),
          self.record("media/unlicensed.png","MEDIA","UNLICENSED"),
          self.record("levels/private_token.json"),
          self.record("media/donor_sound.dll","MEDIA","RIGHTS_UNKNOWN"),
          self.record("localization/api_key.json","LOCALIZATION_JSON"),
        ]
        result=validate_preview_file_inventory(cases)
        self.assertEqual(len(result["acceptedForFurtherInspection"]),0)
        self.assertEqual(len(result["denied"]),len(cases))
        self.assertFalse(result["productionReleaseAuthorized"])
    def test_path_escape_and_case_collision_fails_closed(self):
        for path in ("../file.json","levels/../../x.json","levels//file.json",
                     "C:/temp/file.json","levels/x\\evil.json","levels/%2e%2e/file.json"):
            with self.subTest(path=path),self.assertRaises(ValueError):
                validate_preview_file_inventory([self.record(path)])
        with self.assertRaises(ValueError):
            validate_preview_file_inventory([self.record("levels/A.json"),self.record("levels/a.json")])

if __name__=="__main__":
    unittest.main()

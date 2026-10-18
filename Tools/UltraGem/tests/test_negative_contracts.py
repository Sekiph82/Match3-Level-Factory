"""LFX-M07-001 and M07-007 negative paths before Engine authority exists."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import leveldraft
from preview_pack import build_preview_pack
from preview_diff import diff_preview_manifests
from reference_analysis import analyze_ranked_output

class CanonicalNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        cls.original=leveldraft.loads_strict(p.read_text(encoding="utf-8"))
    def test_real_fixture_golden_and_reordered_field_stability(self):
        d=copy.deepcopy(self.original)
        self.assertEqual(leveldraft.sha256(d),"fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d")
        shuffled={k:d[k] for k in reversed(list(d))}
        self.assertEqual(leveldraft.sha256(shuffled),leveldraft.sha256(d))
        self.assertEqual(leveldraft.loads_strict(leveldraft.dumps_canonical(d)),d)
    def test_duplicate_json_truncated_array_unknown_engine_version_fail(self):
        base=leveldraft.dumps_canonical(self.original)
        with self.assertRaises(leveldraft.DraftError):
            leveldraft.loads_strict('{"draftVersion":1,"draftVersion":1}')
        invalid=copy.deepcopy(self.original)
        invalid["activeMask"]=invalid["activeMask"][:-1]
        with self.assertRaises(leveldraft.DraftError):
            leveldraft.loads_strict(json.dumps(invalid))
        invalid=copy.deepcopy(self.original)
        invalid["engineSchemaVersion"]=1
        with self.assertRaises(leveldraft.DraftError):
            leveldraft.validate(invalid)
        invalid=copy.deepcopy(self.original)
        invalid["goals"][0]["targetCount"]=0
        with self.assertRaises(leveldraft.DraftError):
            leveldraft.validate(invalid)
    def test_preview_pack_invalid_profile_duplicate_identity_and_replay_rejected(self):
        original=self.original
        pack=build_preview_pack([original])
        self.assertFalse(pack["publishAuthorized"])
        with self.assertRaises(ValueError):
            build_preview_pack([original,original])
        forged=copy.deepcopy(pack)
        forged["engineStatus"]="PRODUCTION_CERTIFIED"
        with self.assertRaises(ValueError):
            diff_preview_manifests(pack,forged)
    def test_reference_simulation_loses_hash_gate_on_tampered_candidate(self):
        original=self.original
        candidate={
            "resultStatus":"REFERENCE_ONLY_UNVERIFIED","engineStatus":"BLOCKED_ENG_M24",
            "drafts":[{"draft":original,"draftSha256":"0"*64,
              "profileCompatibility":{"engineStatus":"BLOCKED_ENG_M24","draftMutationPerformed":False}}],
        }
        with self.assertRaises(ValueError):
            analyze_ranked_output(candidate)
    def test_invalid_goal_and_bad_source_are_rejected_without_mutating_original(self):
        original=copy.deepcopy(self.original)
        baseline=leveldraft.sha256(original)
        other=copy.deepcopy(original)
        other["draftVersion"]=2
        with self.assertRaises(leveldraft.DraftError):
            build_preview_pack([other])
        self.assertEqual(leveldraft.sha256(original),baseline)
        self.assertEqual(original,self.original)

if __name__=="__main__":unittest.main()

from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import leveldraft
from reference_batch_explanation import explain_reference_batch

class ReferenceBatchExplanationTests(unittest.TestCase):
    def sample(self):
        fixture=ROOT.parents[1]/"Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json"
        draft=leveldraft.loads_strict(fixture.read_text(encoding="utf-8"))
        return {"resultStatus":"REFERENCE_ONLY_UNVERIFIED","engineStatus":"BLOCKED_ENG_M24",
            "seed":712,"configuration":{"rows":8,"columns":8,"runsPerPolicy":8},
            "drafts":[{"ordinal":1,"rankingStatus":"RANKED_REFERENCE_HEURISTIC",
                "difficultyHypothesis":0.3,"draft":draft,"draftSha256":leveldraft.sha256(draft),
                "profileCompatibility":{"engineStatus":"BLOCKED_ENG_M24",
                                         "localPolicyStatus":"REJECTED_BY_BUILDER_POLICY",
                                         "draftMutationPerformed":False}}],
            "rejectedCandidates":[]}
    def test_real_seed_fixture_still_reports_missing_five_persona_authority(self):
        r=explain_reference_batch(self.sample())
        self.assertEqual(r["candidateCount"],1)
        self.assertFalse(r["fivePersonaMetricsAvailable"])
        self.assertFalse(r["releaseAuthorized"])
        x=r["rankingExplanations"][0]
        self.assertEqual(x["localCapabilityDecision"],"REJECTED_BY_BUILDER_POLICY")
        self.assertEqual(x["donorDifficultyHypothesis"],0.3)
        self.assertEqual(len(x["donorPoliciesAvailable"]),4)
        self.assertEqual(len(x["productionPersonasNotEvaluated"]),5)
        self.assertFalse(x["productionCandidateApproved"])
        self.assertEqual(r,explain_reference_batch(self.sample()))
    def test_wrong_hash_or_certification_rejected(self):
        s=self.sample()
        s["drafts"][0]["draftSha256"]="a"*64
        with self.assertRaises(ValueError):explain_reference_batch(s)
        s=self.sample();s["resultStatus"]="ENGINE_CERTIFIED"
        with self.assertRaises(ValueError):explain_reference_batch(s)
        s=self.sample();s["drafts"][0]["profileCompatibility"]["engineStatus"]="PASS"
        with self.assertRaises(ValueError):explain_reference_batch(s)

if __name__=="__main__":unittest.main()

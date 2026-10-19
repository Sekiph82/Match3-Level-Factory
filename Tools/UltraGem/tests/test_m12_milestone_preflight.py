"""All M12 tasks as one offline LiveOps preflight, never backend authority."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from age_liveops_policy import FLAGS
from m12_milestone_preflight import TASK_IDS, preflight_m12_milestone
from theme_contract import PROFILES


class M12MilestonePreflightTests(unittest.TestCase):
    def policies(self):
        flags = {x: False for x in FLAGS}
        caps = dict(
            adsPerSession=0, earnedPacksPerDay=2, collectionItems=30,
            eventDurationHours=72, streakPressureEnabled=False,
            forcedOfferPopups=0, premiumRewardCount=0,
            personalizedEngagement=False,
        )
        return {p: {"flags": dict(flags), "caps": dict(caps)} for p in PROFILES}

    def event(self, profile, eid="weekly.01", previous=False):
        return dict(
            profileId=profile, eventId=eid, cadence="WEEKLY",
            timezoneId="Europe/Istanbul", startLocal="2026-10-19T09:00:00",
            endLocal="2026-10-20T09:00:00", startFold=None, endFold=None,
            contentKind="LEVEL", contentId="level.001",
            claimPreviouslyRecordedByCaller=previous,
        )

    def call(self, **changes):
        values = dict(
            events=[self.event(p) for p in PROFILES],
            policies=self.policies(),
            available_content={p: ["level.001"] for p in PROFILES},
            observed_server_utc="2026-10-19T10:00:00Z",
            manifest_sha256="a" * 64, git_commit_sha="b" * 40,
        )
        values.update(changes)
        return preflight_m12_milestone(**values)

    def test_thirteen_tasks_in_one_five_title_deterministic_no_grant(self):
        r = self.call()
        self.assertEqual(set(r["taskEvidenceMatrix"]), set(TASK_IDS))
        self.assertEqual(len(r["allFiveProfilePolicyDiagnostics"]), 5)
        self.assertEqual(r["eventCount"], 5)
        self.assertEqual(r["resultStatus"], "M12_OFFLINE_EVENT_POLICY_PREVIEW_ONLY")
        self.assertTrue(all(x["displayStatus"] == "ACTIVE_DISPLAY_PREVIEW_NO_GRANT"
                            for x in r["eventPreviews"]))
        self.assertTrue(all(not x["rewardOrEntitlementGranted"] for x in r["eventPreviews"]))
        for key in ("rewardOrPremiumEntitlementGranted", "userIdentifiersProcessed",
                    "kidBehavioralAdsEnabled", "remoteConfigPublished",
                    "signedConfigCreated", "ownerApprovalVerified",
                    "officialMilestonePass", "actualServerTimeAttested",
                    "authoritativeClaimIdempotencyProved"):
            self.assertIs(r[key], False, key)
        self.assertEqual(r["engineStatus"], "BLOCKED_ENG_M24")
        self.assertEqual(r, self.call(events=list(reversed([self.event(p) for p in PROFILES]))))

    def test_previous_claim_boolean_and_repeat_preview_never_grant(self):
        events = [self.event("Coral_Rescue", previous=True)]
        r = self.call(events=events)
        self.assertEqual(r["eventPreviews"][0]["displayStatus"],
                         "ACTIVE_PREVIOUSLY_RECORDED_BY_CALLER_DISPLAY_ONLY")
        self.assertFalse(r["eventPreviews"][0]["actualClaimHistoryChecked"])
        self.assertFalse(r["eventPreviews"][0]["idempotentBackendProof"])
        self.assertFalse(r["rewardOrPremiumEntitlementGranted"])
        self.assertEqual(r, self.call(events=events))

    def test_future_expired_stopped_and_missing_content_fail_display_only(self):
        one = self.event("Dino_Islands", "future.01")
        one["startLocal"] = "2026-10-22T10:00:00"
        one["endLocal"] = "2026-10-23T10:00:00"
        expired = self.event("Coral_Rescue", "expired.01")
        expired["startLocal"] = "2026-10-14T10:00:00"
        expired["endLocal"] = "2026-10-15T10:00:00"
        missing = self.event("Garage_Legends", "missing.01")
        stopped = self.event("Wonder_Pop", "stopped.01")
        r = self.call(events=[one, expired, missing, stopped],
            available_content={
                **{p: ["level.001"] for p in PROFILES},
                "Garage_Legends": [],
            }, disabled_event_ids=["Wonder_Pop/stopped.01"])
        labels = {e["eventId"]: e["displayStatus"] for e in r["eventPreviews"]}
        self.assertEqual(labels["future.01"], "SCHEDULED_PREVIEW")
        self.assertEqual(labels["expired.01"], "EXPIRED_PREVIEW")
        self.assertEqual(labels["missing.01"], "MISSING_REFERENCED_CONTENT_DISPLAY_DISABLED")
        self.assertEqual(labels["stopped.01"], "STOPPED_BY_LOCAL_PREVIEW_REQUEST_NO_GRANT")
        self.assertFalse(r["remoteConfigPublished"])
        with self.assertRaises(ValueError):
            self.call(events=[stopped], disabled_event_ids=["Wonder_Pop/notfound.01"])

    def test_dst_ambiguous_and_nonexistent_windows_fail_closed(self):
        sample = self.event("The_Fractured_Realms", "dst.01")
        sample.update(timezoneId="Europe/Berlin",
                      startLocal="2026-03-29T02:30:00",
                      endLocal="2026-03-29T04:00:00")
        with self.assertRaisesRegex(ValueError, "nonexistent"):
            self.call(events=[sample])
        sample["startLocal"] = "2026-10-25T02:30:00"
        sample["endLocal"] = "2026-10-25T04:00:00"
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.call(events=[sample])
        sample["startFold"] = 0
        first = self.call(events=[sample])
        sample["startFold"] = 1
        last = self.call(events=[sample])
        self.assertNotEqual(first["eventPreviews"][0]["startUtc"],
                            last["eventPreviews"][0]["startUtc"])
        self.assertFalse(first["recurringOccurrencesExpanded"])

    def test_wonder_child_and_other_unreviewed_age_sensitive_flags_rejected(self):
        for profile in PROFILES:
            prefs = self.policies()
            prefs[profile]["flags"]["personalizedAds"] = True
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                self.call(policies=prefs)
        prefs = self.policies()
        prefs["Wonder_Pop"]["caps"]["eventDurationHours"] = 12
        with self.assertRaises(ValueError):
            self.call(policies=prefs)
        prefs = self.policies()
        prefs["Wonder_Pop"]["caps"]["adsPerSession"] = 1
        with self.assertRaises(ValueError):
            self.call(policies=prefs)

    def test_optional_experiment_is_nonpersonalized_no_assignment_or_grant(self):
        exp = dict(
            gameProfileId="Wonder_Pop", experimentId="local.config.01",
            variants=[
                dict(variantId="A", weightPercent=45, configReference="Review/config-A"),
                dict(variantId="B", weightPercent=45, configReference="Review/config-B"),
            ], holdoutPercent=10,
            audienceMode="NON_PERSONALIZED_OPT_IN_ONLY",
            rollbackReference="Review/rollback-plan")
        r = self.call(experiments=[exp])
        self.assertEqual(len(r["experimentPreviews"]), 1)
        self.assertTrue(r["experimentPreviews"][0]["requiresConsentBeforeEligibility"])
        self.assertFalse(r["experimentPreviews"][0]["stableAllocatorImplemented"])
        exp["audienceMode"] = "BEHAVIORAL_TARGETING"
        with self.assertRaises(ValueError):
            self.call(experiments=[exp])
        exp["audienceMode"] = "NON_PERSONALIZED_OPT_IN_ONLY"
        exp["variants"][0]["weightPercent"] = 44
        with self.assertRaises(ValueError):
            self.call(experiments=[exp])

    def test_duplicate_event_or_bad_schema_or_unsupported_grant_rejected(self):
        sample = self.event("Coral_Rescue")
        bad = [
            [sample, copy.deepcopy(sample)],
            [dict(sample, contentKind="PREMIUM_ENTITLEMENT")],
            [dict(sample, claimPreviouslyRecordedByCaller="false")],
            [dict(sample, rewardCoinGrant=500)],
            [dict(sample, contentId="../../secret")],
        ]
        for group in bad:
            with self.subTest(case=str(group)[:100]), self.assertRaises(ValueError):
                self.call(events=group)
        with self.assertRaises(ValueError):
            self.call(available_content={
                **{p: ["level.001"] for p in PROFILES},
                "Coral_Rescue": ["level.001", "level.001"]})

    def test_unverified_server_and_signature_metadata_rejected(self):
        for observed in ("2026-10-19T10:00:00+00:00", "2026-10-19T10:00Z",
                         "2026-02-31T00:00:00Z", "wrong"):
            with self.assertRaises(ValueError):
                self.call(observed_server_utc=observed)
        with self.assertRaises(ValueError):
            self.call(git_commit_sha="incorrect")
        with self.assertRaises(ValueError):
            self.call(manifest_sha256="A" * 64)
        with self.assertRaises(ValueError):
            self.call(owner_review_reference="Owner\nAPPROVED")
        note = self.call(owner_review_reference="Owner/awaiting-signoff")
        self.assertEqual(note["ownerReviewReferenceUnverified"],
                         "Owner/awaiting-signoff")
        self.assertFalse(note["ownerApprovalVerified"])

if __name__ == "__main__":
    unittest.main()

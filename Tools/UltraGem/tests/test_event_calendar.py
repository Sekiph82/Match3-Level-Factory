from __future__ import annotations
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from event_calendar import propose_calendar_event,preview_event_window


class EventCalendarTests(unittest.TestCase):
    def defaults(self):
        return dict(profile_id="Coral_Rescue",event_id="weekly.coral.01",
                    cadence="WEEKLY",timezone_id="Europe/Istanbul",
                    start_local="2026-10-19T09:00:00",end_local="2026-10-20T09:00:00")
    def test_explicit_utc_preview_and_offline_no_grant(self):
        result=propose_calendar_event(**self.defaults())
        self.assertEqual(result["startUtc"],"2026-10-19T06:00:00Z")
        self.assertEqual(preview_event_window(result,observed_server_utc="2026-10-19T10:00:00Z"),
                         "ACTIVE_DISPLAY_PREVIEW_NO_GRANT")
        self.assertEqual(preview_event_window(result,observed_server_utc="2026-10-18T10:00:00Z"),
                         "SCHEDULED_PREVIEW")
        self.assertEqual(preview_event_window(result,observed_server_utc="2026-10-21T10:00:00Z"),
                         "EXPIRED_PREVIEW")
        self.assertFalse(result["rewardsOrClaimsGenerated"])
        self.assertFalse(result["publishAuthorized"])
    def test_nonexistent_and_ambiguous_dst_are_handled_explicitly(self):
        src=self.defaults()
        src.update(timezone_id="Europe/Berlin",start_local="2026-03-29T02:30:00",
                   end_local="2026-03-29T04:00:00")
        with self.assertRaisesRegex(ValueError,"nonexistent"):
            propose_calendar_event(**src)
        src.update(start_local="2026-10-25T02:30:00",end_local="2026-10-25T04:00:00")
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            propose_calendar_event(**src)
        before=propose_calendar_event(**src,start_fold=0)
        after=propose_calendar_event(**src,start_fold=1)
        self.assertNotEqual(before["startUtc"],after["startUtc"])
        self.assertEqual(before["endUtc"],after["endUtc"])
    def test_invalid_cadence_or_reverse_end_rejected(self):
        src=self.defaults()
        with self.assertRaises(ValueError):
            propose_calendar_event(**dict(src,cadence="EVERY_5_SECONDS"))
        with self.assertRaises(ValueError):
            propose_calendar_event(**dict(src,end_local="2026-10-18T09:00:00"))
        with self.assertRaises(ValueError):
            propose_calendar_event(**dict(src,timezone_id="Mars/Olympus"))


if __name__=="__main__":
    unittest.main()

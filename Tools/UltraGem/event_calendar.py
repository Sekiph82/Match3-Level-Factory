"""Timezone-aware, dry-run event scheduling without claims/grants.

LFX-M12-002. Calendar proposal only; remote authoritative server time,
ENGINE ENG-M20 live event schema and anti-duplicate grant logic are NOT
implemented. DST gaps and ambiguous wall times fail closed without explicit fold.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

from theme_contract import PROFILES

_VALID_CADENCES={"DAILY","WEEKLY","SEASONAL"}


def _to_utc(local_iso: str, zone: ZoneInfo, fold: int | None) -> datetime:
    if not isinstance(local_iso,str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",local_iso) is None:
        raise ValueError("local timestamp must be exact YYYY-MM-DDTHH:MM:SS")
    try:
        local=datetime.fromisoformat(local_iso)
    except ValueError as exc:
        raise ValueError("invalid calendar timestamp") from exc
    choices=[]
    for candidate_fold in (0,1):
        tagged=local.replace(tzinfo=zone,fold=candidate_fold)
        converted=tagged.astimezone(timezone.utc)
        back=converted.astimezone(zone).replace(tzinfo=None)
        if back==local:
            choices.append((candidate_fold,converted))
    if not choices:
        raise ValueError("nonexistent local wall time due to DST transition")
    if len(choices)==2 and choices[0][1]!=choices[1][1] and fold is None:
        raise ValueError("ambiguous DST time requires explicit fold 0/1")
    if fold is not None and (type(fold) is not int or fold not in (0,1)):
        raise ValueError("fold must be 0, 1 or null")
    requested=0 if fold is None else fold
    for candidate,converted in choices:
        if candidate==requested:
            return converted
    raise ValueError("selected DST fold is invalid")


def propose_calendar_event(*, profile_id: str, event_id: str, cadence: str,
                           timezone_id: str, start_local: str, end_local: str,
                           start_fold: int | None = None, end_fold: int | None = None):
    if profile_id not in PROFILES:
        raise ValueError("unknown game profile")
    if not isinstance(event_id,str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{2,79}",event_id) is None:
        raise ValueError("invalid event identity")
    if cadence not in _VALID_CADENCES:
        raise ValueError("cadence must be DAILY, WEEKLY or SEASONAL")
    if not isinstance(timezone_id,str) or not 1<=len(timezone_id)<=100:
        raise ValueError("IANA timezone is required")
    try:
        zone=ZoneInfo(timezone_id)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("unknown IANA timezone") from exc
    start=_to_utc(start_local,zone,start_fold)
    end=_to_utc(end_local,zone,end_fold)
    if not start < end:
        raise ValueError("event end must follow start in UTC")
    if (end-start).total_seconds()>366*86400:
        raise ValueError("preview event duration exceeds one year")
    return {
        "schemaVersion":1,
        "resultStatus":"CALENDAR_EVENT_PREVIEW_ONLY",
        "engineStatus":"BLOCKED_ENG_M24",
        "profileId":profile_id,"eventId":event_id,"cadence":cadence,
        "timezoneId":timezone_id,
        "startLocal":start_local,"endLocal":end_local,
        "startFold":start_fold,"endFold":end_fold,
        "startUtc":start.isoformat().replace("+00:00","Z"),
        "endUtc":end.isoformat().replace("+00:00","Z"),
        "offlineFallback":"CACHED_DISPLAY_ONLY_NEVER_GRANT",
        "engineRemoteEventContractValidated":False,
        "rewardsOrClaimsGenerated":False,
        "publishAuthorized":False,
    }


def preview_event_window(schedule: dict, *, observed_server_utc: str) -> str:
    """Human explanation, never claims actual server time or grants."""
    if not isinstance(schedule,dict) or schedule.get("resultStatus")!="CALENDAR_EVENT_PREVIEW_ONLY":
        raise ValueError("calendar proposal required")
    if not isinstance(observed_server_utc,str) or not observed_server_utc.endswith("Z"):
        raise ValueError("explicit UTC server sample required")
    try:
        observed=datetime.fromisoformat(observed_server_utc.replace("Z","+00:00"))
        start=datetime.fromisoformat(schedule["startUtc"].replace("Z","+00:00"))
        end=datetime.fromisoformat(schedule["endUtc"].replace("Z","+00:00"))
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("invalid UTC sample") from exc
    if observed<start:return "SCHEDULED_PREVIEW"
    if observed>=end:return "EXPIRED_PREVIEW"
    return "ACTIVE_DISPLAY_PREVIEW_NO_GRANT"

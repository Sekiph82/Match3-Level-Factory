"""Level Factory -> Engine content-metadata envelope adapter (LFX-M12-001/008, LFX-M14-002).

Producer side of the MATCH3_ENGINE ENG-M20-010 wire contract
(Packages/com.match3.engine/Runtime/LiveOps/ContentMetadataReceiver.cs, pinned at
Engine commit ENGINE_CONTRACT_SHA). Everything below that validates is a MIRROR of
the Engine receiver so the Factory fails closed before export; the Engine stays
authoritative and re-validates every envelope. Unsigned only: the payloadSha256 is
an unkeyed integrity digest, not authentication. No signing, network or cloud write.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Iterable

import leveldraft

ENGINE_CONTRACT_SHA = "5f5aaac37a844b2d152dcc1a07e0c962a1b47ace"
SCHEMA_VERSION = "1.0"
PRODUCER_ID = "Match3-Level-Factory"
SUPPORTED_SCHEMA_MAJOR = 1
MAX_ITEMS = 512
MAX_UTF8_BYTES = 256 * 1024
MAX_DEPTH = 32
# Mirror of Engine GameProfileCatalog ids (Runtime/GameProfiles.cs).
GAME_IDS = ("Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop")
KINDS = ("World", "Level", "Event")
GOAL_KINDS = ("CollectPiece", "ClearObstacle", "RescueDrop")

_ENVELOPE_FIELDS = ("gameId", "items", "producerId", "schemaVersion")
_ITEM_FIELDS = ("contentId", "contentKind", "contentVersion", "payload", "payloadSha256")
_PAYLOAD_FIELDS = {
    "World": ("order",),
    "Level": ("moves", "objectives", "obstacleIds", "order", "worldId"),
    "Event": ("endUtc", "levelIds", "startUtc"),
}
_OBJECTIVE_FIELDS = ("count", "kind", "targetId")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{2,79}\Z")
_KEY = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_UINT = re.compile(r"(0|[1-9][0-9]{0,3})\Z")
_INT64 = (-2**63, 2**63 - 1)

# Mirror of ContentMetadataReceiver.ForbiddenWords / ForbiddenSubstrings at ENGINE_CONTRACT_SHA.
_FORBIDDEN_WORDS = frozenset({
    "price", "pricing", "sku", "iap", "inapp", "receipt", "purchase", "currency", "credential", "secret",
    "token", "password", "apikey", "payment", "billing", "transaction", "paid", "bearer", "auth",
    "authorization", "authorisation", "productid", "storeproduct", "storesku", "privatekey", "pwd",
    "offer", "ssn",
})
_FORBIDDEN_SUBSTRINGS = (
    "price", "receipt", "purchase", "credential", "password", "passwd", "apikey", "productid",
    "storeproduct", "privatekey", "payment", "billing", "transaction", "bearer",
    "accesstoken", "clientsecret", "authheader", "skuid", "iapid", "accesskey", "signingkey",
    "paidcurrency", "paidcoin", "paidgem", "paiditem",
    "hardcurrency", "premiumcurrency", "realcurrency",
    "creditcard", "cardnumber", "walletaddress", "iban", "cvv",
    "paywall", "offerid",
    "bankaccount", "routingnumber", "sortcode", "paypal", "stripekey", "taxid", "cardno",
)


class EnvelopeError(ValueError):
    """code is an Engine ContentMetadataReasons string; items holds (index, code, detail)."""

    def __init__(self, code: str, detail: str = "", items: Iterable[tuple[int, str, str]] = ()):
        self.code, self.detail, self.items = code, detail, list(items)
        extra = "; ".join(f"[{i}] {c} {d}".rstrip() for i, c, d in self.items)
        super().__init__(" ".join(x for x in (code, detail, extra) if x))


# ---- canonical JSON / digest -------------------------------------------------

def _check_tree(node: Any, depth: int = 0) -> None:
    """Values the Engine reader can represent: objects, arrays, strings, int64, bool, null."""
    if depth > MAX_DEPTH:
        raise EnvelopeError("MalformedDocument", "nesting too deep")
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str) or _KEY.fullmatch(key) is None:
                raise EnvelopeError("MalformedDocument", f"invalid key {key!r}")
            _check_tree(value, depth + 1)
    elif isinstance(node, list):
        for value in node:
            _check_tree(value, depth + 1)
    elif isinstance(node, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in node):
            raise EnvelopeError("MalformedDocument", "unpaired surrogate")
    elif isinstance(node, bool) or node is None:
        pass
    elif type(node) is int:
        if not _INT64[0] <= node <= _INT64[1]:
            raise EnvelopeError("MalformedDocument", "integer out of range")
    else:  # float, Decimal, tuple, ...
        raise EnvelopeError("MalformedDocument", "non-integer number" if isinstance(node, float)
                            else "unsupported value type " + type(node).__name__)


def canonical_json(value: Any) -> str:
    """Byte-identical to Engine CanonicalJson.Serialize: sorted keys, compact, ASCII escapes."""
    _check_tree(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def payload_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def loads_strict(text: str) -> Any:
    """Mirror of the Engine strict reader; every defect is MalformedDocument."""
    if not isinstance(text, str) or len(text.encode("utf-8", "surrogatepass")) > MAX_UTF8_BYTES:
        raise EnvelopeError("MalformedDocument", f"input exceeds {MAX_UTF8_BYTES} UTF-8 bytes")

    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise EnvelopeError("MalformedDocument", "duplicate key " + key)
            obj[key] = value
        return obj

    def no_float(text):
        raise EnvelopeError("MalformedDocument", "non-integer number " + text)

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_float=no_float, parse_constant=no_float)
    except json.JSONDecodeError as exc:
        raise EnvelopeError("MalformedDocument", str(exc)) from exc
    _check_tree(value)
    return value


def dumps(envelope: dict[str, Any]) -> str:
    """Stable pretty file form (Engine accepts any JSON whitespace); ASCII only."""
    _check_tree(envelope)
    return json.dumps(envelope, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


# ---- Engine rule mirrors -------------------------------------------------------

def is_valid_id(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _split_words(key: str, split_acronym_end: bool) -> list[str]:
    words, current = [], ""
    for i, c in enumerate(key):
        boundary = c in "-_" or (c.isupper() and i > 0 and (
            key[i - 1].islower() or
            (split_acronym_end and key[i - 1].isupper() and i + 1 < len(key) and key[i + 1].islower())))
        if boundary and current:
            words.append(current)
            current = ""
        if c not in "-_":
            current += c.lower()
    if current:
        words.append(current)
    return words


def _forbidden_word(w: str) -> bool:
    return w in _FORBIDDEN_WORDS or (len(w) > 1 and w.endswith("s") and w[:-1] in _FORBIDDEN_WORDS)


def is_forbidden_key(key: str) -> bool:
    """Mirror of ContentMetadataReceiver.IsForbiddenKey (Engine remains authoritative)."""
    if not key:
        return False
    compact = key.replace("-", "").replace("_", "").lower()
    if any(sub in compact for sub in _FORBIDDEN_SUBSTRINGS):
        return True
    for words in (_split_words(key, False), _split_words(key, True)):
        for i, w in enumerate(words):
            if _forbidden_word(w) or (i + 1 < len(words) and _forbidden_word(w + words[i + 1])):
                return True
    return False


def parse_utc(value: Any) -> datetime:
    """Exact yyyy-MM-ddTHH:mm:ssZ; fractional seconds, offsets and other ISO forms are rejected."""
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise ValueError("timestamp must be exact yyyy-MM-ddTHH:mm:ssZ (no fractional seconds)")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def game_id_for_profile(profile_id: str) -> str:
    """Factory profileId -> Engine gameId (identity on the Engine catalog, fail closed otherwise)."""
    if profile_id not in GAME_IDS:
        raise EnvelopeError("GameMismatch", f"unknown game id {profile_id!r}")
    return profile_id


class _Reject(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail)
        self.code, self.detail = code, detail


def _reject_forbidden(node: Any) -> None:
    if isinstance(node, dict):
        for key in sorted(node):
            if is_forbidden_key(key):
                raise _Reject("ForbiddenMonetizationField", key)
            _reject_forbidden(node[key])
    elif isinstance(node, list):
        for value in node:
            _reject_forbidden(value)


def _known_fields(obj: dict, known: tuple[str, ...]) -> None:
    for key in sorted(obj):
        if key not in known and not key.startswith("x-"):
            raise _Reject("UnknownPayloadField", key)
    for key in known:
        if key not in obj:
            raise _Reject("MissingField", key)


def _int(obj: dict, key: str, lo: int, hi: int) -> int:
    if key not in obj:
        raise _Reject("MissingField", key)
    v = obj[key]
    if type(v) is not int:
        raise _Reject("FieldTypeInvalid", key)
    if not lo <= v <= hi:
        raise _Reject("ValueOutOfRange", key)
    return v


def _id(obj: dict, key: str) -> str:
    if key not in obj:
        raise _Reject("MissingField", key)
    if not isinstance(obj[key], str):
        raise _Reject("FieldTypeInvalid", key)
    if not is_valid_id(obj[key]):
        raise _Reject("IdInvalid", key)
    return obj[key]


def _list(obj: dict, key: str, lo: int, hi: int) -> list:
    if key not in obj:
        raise _Reject("MissingField", key)
    if not isinstance(obj[key], list):
        raise _Reject("FieldTypeInvalid", key)
    if not lo <= len(obj[key]) <= hi:
        raise _Reject("ValueOutOfRange", key)
    return obj[key]


def _id_list(obj: dict, key: str, lo: int, hi: int) -> list[str]:
    ids = _list(obj, key, lo, hi)
    for v in ids:
        if not isinstance(v, str):
            raise _Reject("FieldTypeInvalid", key)
        if not is_valid_id(v):
            raise _Reject("IdInvalid", key)
    if len(set(ids)) != len(ids):
        raise _Reject("DuplicateContentId", key)
    return ids


def _utc(obj: dict, key: str) -> datetime:
    if key not in obj:
        raise _Reject("MissingField", key)
    try:
        return parse_utc(obj[key])
    except ValueError:
        raise _Reject("EventWindowMalformed", key) from None


def _parse_item(raw: Any, allowed: frozenset[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _Reject("FieldTypeInvalid", "item is not an object")
    _reject_forbidden(raw)
    for key in sorted(raw):
        if key not in _ITEM_FIELDS:
            raise _Reject("UnknownField", key)
    kind = raw.get("contentKind")
    if not isinstance(kind, str):
        raise _Reject("FieldTypeInvalid" if "contentKind" in raw else "MissingField", "contentKind")
    if kind not in KINDS:
        raise _Reject("UnknownContentKind", kind)
    if kind not in allowed:
        raise _Reject("ContentKindNotAllowed", kind)
    item = {"kind": kind, "id": _id(raw, "contentId"), "version": _int(raw, "contentVersion", 1, 2**31 - 1)}
    if "payload" not in raw:
        raise _Reject("MissingField", "payload")
    payload = raw["payload"]
    if not isinstance(payload, dict):
        raise _Reject("FieldTypeInvalid", "payload")
    _known_fields(payload, _PAYLOAD_FIELDS[kind])
    if kind == "World":
        item["order"] = _int(payload, "order", 1, 100000)
    elif kind == "Level":
        item["worldId"] = _id(payload, "worldId")
        item["order"] = _int(payload, "order", 1, 100000)
        _int(payload, "moves", 1, 999)
        for objective in _list(payload, "objectives", 1, 8):
            if not isinstance(objective, dict):
                raise _Reject("FieldTypeInvalid", "objective")
            _known_fields(objective, _OBJECTIVE_FIELDS)
            if objective["kind"] not in GOAL_KINDS:
                raise _Reject("ValueOutOfRange", "objective.kind")
            _id(objective, "targetId")
            _int(objective, "count", 1, 9999)
        _id_list(payload, "obstacleIds", 0, 32)
    else:
        if _utc(payload, "startUtc") >= _utc(payload, "endUtc"):
            raise _Reject("EventWindowInverted", "startUtc >= endUtc")
        item["levelIds"] = _id_list(payload, "levelIds", 1, 256)
    computed = payload_sha256(payload)
    if "payloadSha256" in raw:
        digest = raw["payloadSha256"]
        if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
            raise _Reject("DigestMalformed", "payloadSha256")
        if digest != computed:
            raise _Reject("DigestMismatch", "computed " + computed)
    return item


def validate_envelope(doc: Any, *, game_id: str, allowed_kinds: Iterable[str] = KINDS,
                      known_world_ids: Iterable[str] = (), known_level_ids: Iterable[str] = ()) -> None:
    """Mirror of ContentMetadataReceiver.Receive for an empty receiver (no applied state).

    known_*_ids mirror the receiver's build-shipped reference targets. Version
    regression/conflict against previously applied content is receiver state and
    is NOT checked here. Raises EnvelopeError with the Engine reason code.
    """
    if game_id not in GAME_IDS:
        raise EnvelopeError("GameMismatch", f"unknown receiver game {game_id!r}")
    allowed = frozenset(allowed_kinds)
    known_worlds, known_levels = set(known_world_ids), set(known_level_ids)
    if not allowed <= set(KINDS) or not all(map(is_valid_id, known_worlds | known_levels)):
        raise ValueError("invalid receiver configuration")
    _check_tree(doc)
    if not isinstance(doc, dict):
        raise EnvelopeError("MalformedDocument", "root is not an object")
    for key in sorted(doc):
        if is_forbidden_key(key):
            raise EnvelopeError("ForbiddenMonetizationField", key)
        if key not in _ENVELOPE_FIELDS:
            raise EnvelopeError("UnknownField", key)
    for key in _ENVELOPE_FIELDS:
        if key not in doc:
            raise EnvelopeError("MissingField", key)
    schema = doc["schemaVersion"]
    parts = schema.split(".") if isinstance(schema, str) else []
    if len(parts) != 2 or not all(_UINT.fullmatch(p) for p in parts):
        raise EnvelopeError("SchemaVersionMalformed", "schemaVersion")
    if int(parts[0]) != SUPPORTED_SCHEMA_MAJOR:
        raise EnvelopeError("SchemaMajorUnsupported", schema)
    producer = doc["producerId"]
    if not isinstance(producer, str) or not 1 <= len(producer) <= 128 or any(not "!" <= c <= "~" for c in producer):
        raise EnvelopeError("ProducerIdInvalid", "producerId")
    if not isinstance(doc["gameId"], str):
        raise EnvelopeError("FieldTypeInvalid", "gameId")
    if doc["gameId"] != game_id:
        raise EnvelopeError("GameMismatch", "expected " + game_id)
    raw_items = doc["items"]
    if not isinstance(raw_items, list):
        raise EnvelopeError("FieldTypeInvalid", "items")
    if not raw_items:
        raise EnvelopeError("EmptyBatch")
    if len(raw_items) > MAX_ITEMS:
        raise EnvelopeError("BatchTooLarge", str(len(raw_items)))

    parsed: list[dict | None] = []
    reasons: list[tuple[str, str] | None] = []
    seen: set[str] = set()
    for raw in raw_items:  # pass 1: structure, values, digest, duplicates
        try:
            item = _parse_item(raw, allowed)
            if item["id"] in seen:
                raise _Reject("DuplicateContentId", item["id"])
            seen.add(item["id"])
            parsed.append(item)
            reasons.append(None)
        except _Reject as r:
            parsed.append(None)
            reasons.append((r.code, r.detail))

    worlds = {x["id"] for x in parsed if x and x["kind"] == "World"} | known_worlds
    levels = {x["id"] for x in parsed if x and x["kind"] == "Level"} | known_levels
    slots: dict[str, str] = {}
    for i, item in enumerate(parsed):  # pass 2: references and order slots
        if item is None:
            continue
        if item["kind"] == "Level" and item["worldId"] not in worlds:
            reasons[i] = ("DanglingReference", "worldId " + item["worldId"])
            continue
        missing = [lv for lv in item.get("levelIds", ()) if lv not in levels]
        if missing:
            reasons[i] = ("DanglingReference", "levelId " + missing[0])
            continue
        slot = ("W|%d" % item["order"] if item["kind"] == "World" else
                "L|%s|%d" % (item["worldId"], item["order"]) if item["kind"] == "Level" else None)
        if slot is not None:
            if slot in slots:
                reasons[i] = ("DuplicateOrder", f"{slot} held by {slots[slot]}")
                continue
            slots[slot] = item["id"]
    rejected = [(i, r[0], r[1]) for i, r in enumerate(reasons) if r is not None]
    if rejected:
        raise EnvelopeError("ItemRejected", "", rejected)


def validate_text(text: str, **receiver: Any) -> dict[str, Any]:
    doc = loads_strict(text)
    validate_envelope(doc, **receiver)
    return doc


# ---- builders from Factory data -------------------------------------------------

def _item(kind: str, content_id: str, version: int, payload: dict, extensions: dict | None,
          digest: bool) -> dict[str, Any]:
    payload = {**payload, **(extensions or {})}
    item = {"contentKind": kind, "contentId": content_id, "contentVersion": version, "payload": payload}
    if digest:
        item["payloadSha256"] = payload_sha256(payload)
    return item


def world_item(world_id: str, *, order: int, content_version: int = 1,
               extensions: dict | None = None, digest: bool = True) -> dict[str, Any]:
    return _item("World", world_id, content_version, {"order": order}, extensions, digest)


def level_item(level_id: str, *, world_id: str, order: int, moves: int,
               objectives: list[dict[str, Any]], obstacle_ids: list[str], content_version: int = 1,
               extensions: dict | None = None, digest: bool = True) -> dict[str, Any]:
    payload = {"worldId": world_id, "order": order, "moves": moves,
               "objectives": [{"kind": o["kind"], "targetId": o["targetId"], "count": o["count"]}
                              for o in objectives],
               "obstacleIds": list(obstacle_ids)}
    return _item("Level", level_id, content_version, payload, extensions, digest)


def level_item_from_draft(draft: dict[str, Any], *, game_id: str, order: int,
                          goal_kinds: dict[str, str], content_version: int = 1,
                          extensions: dict | None = None, digest: bool = True) -> dict[str, Any]:
    """LevelDraft -> Engine Level item. LevelDraft has no goal kind or campaign order,
    so the author supplies both; obstacleIds are the draft's distinct cell obstacles."""
    leveldraft.validate(draft)
    if draft["gameProfileId"] != game_id_for_profile(game_id):
        raise EnvelopeError("GameMismatch", f"draft is for {draft['gameProfileId']}, expected {game_id}")
    goals = leveldraft.canonicalize(draft)["goals"]
    if set(goal_kinds) != {g["goalId"] for g in goals}:
        raise EnvelopeError("MissingField", "goal kind required for every draft goal")
    obstacles = sorted({c["obstacleId"] for c in draft["cells"] if c["obstacleId"] is not None})
    return level_item(draft["levelId"], world_id=draft["worldId"], order=order, moves=draft["moveBudget"],
                      objectives=[{"kind": goal_kinds[g["goalId"]], "targetId": g["targetId"],
                                   "count": g["targetCount"]} for g in goals],
                      obstacle_ids=obstacles, content_version=content_version,
                      extensions=extensions, digest=digest)


def event_item(event_id: str, *, start_utc: str, end_utc: str, level_ids: list[str],
               content_version: int = 1, extensions: dict | None = None,
               digest: bool = True) -> dict[str, Any]:
    payload = {"startUtc": start_utc, "endUtc": end_utc, "levelIds": list(level_ids)}
    return _item("Event", event_id, content_version, payload, extensions, digest)


def event_item_from_calendar(schedule: dict[str, Any], *, game_id: str, level_ids: list[str],
                             content_version: int = 1, extensions: dict | None = None,
                             digest: bool = True) -> dict[str, Any]:
    """event_calendar.propose_calendar_event output -> Engine Event item (UTC window only)."""
    if not isinstance(schedule, dict) or schedule.get("resultStatus") != "CALENDAR_EVENT_PREVIEW_ONLY":
        raise ValueError("calendar proposal required")
    if schedule.get("profileId") != game_id_for_profile(game_id):
        raise EnvelopeError("GameMismatch", f"event is for {schedule.get('profileId')}, expected {game_id}")
    return event_item(schedule["eventId"], start_utc=schedule["startUtc"], end_utc=schedule["endUtc"],
                      level_ids=level_ids, content_version=content_version,
                      extensions=extensions, digest=digest)


def build_envelope(*, game_id: str, producer_id: str, items: list[dict[str, Any]],
                   known_world_ids: Iterable[str] = (), known_level_ids: Iterable[str] = ()) -> dict[str, Any]:
    """Unsigned Engine envelope; validated against the Engine mirror before it is returned."""
    envelope = {"schemaVersion": SCHEMA_VERSION, "producerId": producer_id,
                "gameId": game_id_for_profile(game_id), "items": list(items)}
    validate_envelope(envelope, game_id=game_id, known_world_ids=known_world_ids,
                      known_level_ids=known_level_ids)
    return envelope


def compile_game_envelopes(items_by_game: dict[str, list[dict[str, Any]]], *, producer_id: str,
                           known_world_ids: dict[str, Iterable[str]] | None = None,
                           known_level_ids: dict[str, Iterable[str]] | None = None) -> dict[str, dict[str, Any]]:
    """LFX-M14-002: one unsigned envelope per Engine gameId; all five titles required.

    LiveOps policy, age guards and offer metadata are not Engine content kinds and
    offers/prices are forbidden by the Engine envelope, so they are never compiled in.
    """
    if not isinstance(items_by_game, dict) or set(items_by_game) != set(GAME_IDS):
        raise EnvelopeError("GameMismatch", "content for exactly the five Engine game ids required")
    worlds, levels = known_world_ids or {}, known_level_ids or {}
    if not set(worlds) <= set(GAME_IDS) or not set(levels) <= set(GAME_IDS):
        raise EnvelopeError("GameMismatch", "known ids keyed by unknown game id")
    return {g: build_envelope(game_id=g, producer_id=producer_id, items=items_by_game[g],
                              known_world_ids=worlds.get(g, ()), known_level_ids=levels.get(g, ()))
            for g in GAME_IDS}

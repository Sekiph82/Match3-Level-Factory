"""Parity of the Factory Engine-envelope adapter with pinned Engine ENG-M20-010 fixtures."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine_envelope as ee
from engine_envelope import EnvelopeError
from event_calendar import preview_event_window, propose_calendar_event
from theme_contract import PROFILES

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "engine_m20_010"
CORAL = dict(game_id="Coral_Rescue")

# Engine ContentMetadataReceiverTests.MalformedFixtures at ENGINE_CONTRACT_SHA:
# fixture -> (batch reason, rejected item index or None, item reason)
MALFORMED = {
    "wrong_game.json": ("GameMismatch", None, None),
    "unknown_kind.json": ("ItemRejected", 1, "UnknownContentKind"),
    "bad_schema_major.json": ("SchemaMajorUnsupported", None, None),
    "digest_mismatch.json": ("ItemRejected", 0, "DigestMismatch"),
    "dangling_level_ref.json": ("ItemRejected", 2, "DanglingReference"),
    "inverted_window.json": ("ItemRejected", 2, "EventWindowInverted"),
    "forbidden_price_field.json": ("ItemRejected", 0, "ForbiddenMonetizationField"),
    "unknown_top_level_field.json": ("UnknownField", None, None),
    "duplicate_content_id.json": ("ItemRejected", 1, "DuplicateContentId"),
    "unknown_payload_field.json": ("ItemRejected", 0, "UnknownPayloadField"),
    "non_integer_number.json": ("MalformedDocument", None, None),
    "duplicate_json_key.json": ("MalformedDocument", None, None),
}
# Engine ForbiddenKeyDetection_MatchesWordsAndCompactSubstrings cases at ENGINE_CONTRACT_SHA.
FORBIDDEN = (
    "price x-priceTier sku iapId IAPId SKU storeProductId product_id apiKey receiptData authToken "
    "SKUs IAPs iaps storeSKUs productIds inAppItem paymentRef billingId transactionId paid "
    "bearerToken authHeader authorization storeproductid accesstoken access_token clientsecret "
    "authheader skuid x-sku-id iapid paidcoins x-paidCurrency paidgems paiditem hardcurrency "
    "premiumcurrency realcurrency creditcard cardNumber walletaddress iban x-cvv passwd password "
    "pwd x-pwdHint accesskey signingkey privatekey offer x-offers x-offerId specialofferid paywall "
    "x-paywall x-softPaywallLevel bankAccount routing_number sortCode paypalEmail stripeKey taxId "
    "cardNo ssn x-ssn tokenCount x-secretLevel x-torchBearer x-pricelessGem priceUsd iapCredential"
).split()
ALLOWED = ("x-mediaPath x-editorNote x-coinCost gems authorId authorName producerId "
           "obstacleIds targetId objectives").split()
OBJECTIVES = [{"kind": "CollectPiece", "targetId": "piece.red", "count": 30},
              {"kind": "ClearObstacle", "targetId": "obstacle.ice", "count": 12}]


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def fixture_doc(name: str):
    return json.loads(fixture_text(name))


def draft(level_id="cr.level.0001", profile="Coral_Rescue"):
    """Minimal valid 2x1 LevelDraft carrying an obstacle.ice cell."""
    cells = [
        dict(row=0, column=0, layer=0, active=True, locked=False, contentId="piece.red",
             obstacleId=None, obstacleDurability=0, lockDurability=0, specialId=None),
        dict(row=0, column=1, layer=0, active=True, locked=False, contentId=None,
             obstacleId="obstacle.ice", obstacleDurability=1, lockDurability=0, specialId=None),
    ]
    return dict(
        draftVersion=1, validationStatus="PROTOTYPE_ONLY", gameProfileId=profile, profileVersion=1,
        worldId="cr.world.reef", chapterId="cr.chapter.1", levelId=level_id,
        releaseChannel="local", platform="windows-editor", locale="en", seed=7, width=2, height=1,
        minEngineVersion=None, maxEngineVersion=None, layers=1, activeMask=[True, True],
        moveBudget=25, cells=cells,
        goals=[dict(goalId="g2", targetId="obstacle.ice", targetCount=12),
               dict(goalId="g1", targetId="piece.red", targetCount=30)],
        engineSchemaVersion=None, timedMode=False, timeLimitSeconds=0,
        oneStarThreshold=1, twoStarThreshold=2, threeStarThreshold=3,
        difficultyLabel="normal", editorHintKey=None,
        sourceRepository=None, sourceRevision=None, sourceKind=None)


GOAL_KINDS = {"g1": "CollectPiece", "g2": "ClearObstacle"}


def winter(profile="Coral_Rescue", start="2026-12-01T00:00:00", end="2026-12-08T00:00:00"):
    return propose_calendar_event(profile_id=profile, event_id="cr.event.winter", cadence="WEEKLY",
                                  timezone_id="UTC", start_local=start, end_local=end)


class FixtureParityTests(unittest.TestCase):
    def test_fixture_set_is_complete(self):
        names = {p.name for p in FIXTURES.glob("*.json")}
        self.assertEqual(names, set(MALFORMED) | {"valid_world.json", "valid_level.json", "valid_event.json"})

    def test_every_fixture_digest_recomputes_to_engine_value(self):
        checked = 0
        for name in sorted(MALFORMED) + ["valid_world.json", "valid_level.json", "valid_event.json"]:
            if name in ("non_integer_number.json", "duplicate_json_key.json"):
                continue  # not representable / no digests
            for item in fixture_doc(name)["items"]:
                if "payloadSha256" not in item:
                    continue
                checked += 1
                with self.subTest(fixture=name, item=item["contentId"]):
                    if name == "digest_mismatch.json":
                        self.assertNotEqual(ee.payload_sha256(item["payload"]), item["payloadSha256"])
                    else:
                        self.assertEqual(ee.payload_sha256(item["payload"]), item["payloadSha256"])
        self.assertGreaterEqual(checked, 20)

    def test_valid_fixtures_accepted_by_mirror(self):
        ee.validate_text(fixture_text("valid_world.json"), **CORAL)
        ee.validate_text(fixture_text("valid_level.json"), **CORAL, known_world_ids=["cr.world.reef"])
        ee.validate_text(fixture_text("valid_event.json"), **CORAL)
        ee.validate_text(fixture_text("valid_world.json"), game_id="Coral_Rescue", allowed_kinds=["World"])
        with self.assertRaises(EnvelopeError) as ctx:  # Engine: dangling without known world
            ee.validate_text(fixture_text("valid_level.json"), **CORAL)
        self.assertEqual(ctx.exception.items[0][:2], (0, "DanglingReference"))
        with self.assertRaises(EnvelopeError) as ctx:  # Engine: Wonder_Pop receiver rejects Coral doc
            ee.validate_text(fixture_text("valid_world.json"), game_id="Wonder_Pop")
        self.assertEqual(ctx.exception.code, "GameMismatch")

    def test_malformed_fixtures_rejected_with_engine_reason(self):
        for name, (code, index, item_code) in MALFORMED.items():
            with self.subTest(fixture=name), self.assertRaises(EnvelopeError) as ctx:
                ee.validate_text(fixture_text(name), **CORAL)
            self.assertEqual(ctx.exception.code, code, name)
            if index is not None:
                self.assertEqual([(i, c) for i, c, _ in ctx.exception.items], [(index, item_code)], name)

    def test_builder_reproduces_valid_fixtures_byte_for_byte(self):
        reef = ee.world_item("cr.world.reef", order=1)
        world = ee.build_envelope(game_id="Coral_Rescue", producer_id="fixture-producer/py",
                                  items=[reef, ee.world_item("cr.world.kelp", order=2, digest=False)])
        self.assertEqual(ee.dumps(world), fixture_text("valid_world.json"))

        level = ee.level_item_from_draft(draft(), game_id="Coral_Rescue", order=1, goal_kinds=GOAL_KINDS,
                                         content_version=3,
                                         extensions={"x-editorNote": "authoring tool note é \"quoted\""})
        env = ee.build_envelope(game_id="Coral_Rescue", producer_id="fixture-producer/py", items=[level],
                                known_world_ids=["cr.world.reef"])
        self.assertEqual(ee.dumps(env), fixture_text("valid_level.json"))

        l1 = ee.level_item_from_draft(draft(), game_id="Coral_Rescue", order=1, goal_kinds=GOAL_KINDS)
        l2 = ee.level_item("cr.level.0002", world_id="cr.world.reef", order=2, moves=22,
                           objectives=OBJECTIVES, obstacle_ids=["obstacle.ice"])
        ev = ee.event_item_from_calendar(winter(), game_id="Coral_Rescue",
                                         level_ids=["cr.level.0001", "cr.level.0002"])
        env = ee.build_envelope(game_id="Coral_Rescue", producer_id="fixture-producer/py",
                                items=[reef, l1, l2, ev])
        self.assertEqual(ee.dumps(env), fixture_text("valid_event.json"))

    def test_builder_refuses_each_malformed_fixture_defect(self):
        reef = ee.world_item("cr.world.reef", order=1)
        lvl = dict(world_id="cr.world.reef", order=1, moves=25, objectives=OBJECTIVES,
                   obstacle_ids=["obstacle.ice"])

        def build(items, **kw):
            return ee.build_envelope(game_id="Coral_Rescue", producer_id=ee.PRODUCER_ID, items=items, **kw)

        cases = {
            "forbidden_price_field": (lambda: build([ee.level_item("cr.level.0001", **lvl,
                                                                    extensions={"x-priceUsd": 199})],
                                                    known_world_ids=["cr.world.reef"]),
                                      "ForbiddenMonetizationField"),
            "unknown_payload_field": (lambda: build([ee.level_item("cr.level.0001", **lvl,
                                                                    extensions={"difficulty": 3})],
                                                    known_world_ids=["cr.world.reef"]),
                                      "UnknownPayloadField"),
            "dangling_level_ref": (lambda: build([reef, ee.event_item_from_calendar(
                winter(), game_id="Coral_Rescue", level_ids=["cr.level.9999"])]), "DanglingReference"),
            "duplicate_content_id": (lambda: build([reef, ee.world_item("cr.world.reef", order=2,
                                                                        content_version=2)]),
                                     "DuplicateContentId"),
            "inverted_window": (lambda: build([ee.event_item("cr.event.winter", start_utc="2026-12-08T00:00:00Z",
                                                             end_utc="2026-12-01T00:00:00Z",
                                                             level_ids=["cr.level.0001"])],
                                              known_level_ids=["cr.level.0001"]), "EventWindowInverted"),
            "unknown_kind": (lambda: build([reef, dict(reef, contentKind="Offer", contentId="cr.offer.bundle")]),
                             "UnknownContentKind"),
            "digest_mismatch": (lambda: build([dict(reef, payload={"order": 2})]), "DigestMismatch"),
        }
        for name, (fn, item_code) in cases.items():
            with self.subTest(defect=name), self.assertRaises(EnvelopeError) as ctx:
                fn()
            self.assertEqual(ctx.exception.code, "ItemRejected")
            self.assertIn(item_code, [c for _, c, _ in ctx.exception.items])
        with self.assertRaises(EnvelopeError) as ctx:  # non_integer_number
            build([ee.world_item("cr.world.reef", order=1.5)])
        self.assertEqual(ctx.exception.code, "MalformedDocument")
        with self.assertRaises(EnvelopeError) as ctx:  # wrong_game
            ee.level_item_from_draft(draft(profile="Dino_Islands"), game_id="Coral_Rescue", order=1,
                                     goal_kinds=GOAL_KINDS)
        self.assertEqual(ctx.exception.code, "GameMismatch")
        with self.assertRaises(EnvelopeError) as ctx:
            ee.event_item_from_calendar(winter(profile="Dino_Islands"), game_id="Coral_Rescue",
                                        level_ids=["cr.level.0001"])
        self.assertEqual(ctx.exception.code, "GameMismatch")
        # bad_schema_major / unknown_top_level_field / duplicate_json_key are not constructible by the
        # builder (fixed "1.0", fixed keys, dict input); the validator rejects them on any input.
        good = build([reef])
        for change, code in (({"schemaVersion": "2.0"}, "SchemaMajorUnsupported"),
                             ({"schemaVersion": 1}, "SchemaVersionMalformed"),
                             ({"schemaVersion": "1.00"}, "SchemaVersionMalformed"),
                             ({"signedBy": "someone"}, "UnknownField"),
                             ({"profileId": "Coral_Rescue"}, "UnknownField"),
                             ({"producerId": "has space"}, "ProducerIdInvalid"),
                             ({"items": []}, "EmptyBatch")):
            with self.subTest(change=change), self.assertRaises(EnvelopeError) as ctx:
                ee.validate_envelope(dict(good, **change), **CORAL)
            self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(EnvelopeError) as ctx:
            ee.loads_strict('{"a":1,"a":2}')
        self.assertEqual(ctx.exception.code, "MalformedDocument")


class EngineRuleMirrorTests(unittest.TestCase):
    def test_forbidden_key_mirror_matches_engine_cases(self):
        for key in FORBIDDEN:
            self.assertTrue(ee.is_forbidden_key(key), key)
        for key in ALLOWED:
            self.assertFalse(ee.is_forbidden_key(key), key)

    def test_forbidden_key_rejected_at_any_depth(self):
        lvl = ee.level_item("cr.level.0001", world_id="cr.world.reef", order=1, moves=20,
                            objectives=[dict(OBJECTIVES[0])], obstacle_ids=[])
        lvl["payload"]["objectives"][0]["x-meta"] = {"nested": [{"receiptData": "r"}]}
        with self.assertRaises(EnvelopeError) as ctx:
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[lvl],
                              known_world_ids=["cr.world.reef"])
        self.assertEqual(ctx.exception.items[0][1], "ForbiddenMonetizationField")
        with self.assertRaises(EnvelopeError) as ctx:
            ee.validate_envelope({"schemaVersion": "1.0", "producerId": "p", "gameId": "Coral_Rescue",
                                  "items": [ee.world_item("cr.world.reef", order=1)], "storeProductId": "x"},
                                 **CORAL)
        self.assertEqual(ctx.exception.code, "ForbiddenMonetizationField")

    def test_digest_is_ensure_ascii_true_and_matches_csharp_writer(self):
        payload = {"x-n": "é \U0001F600 \x7f \x01 \"q\" \\ /", "order": 1}

        def csharp(value):  # transcription of Engine CanonicalJson.WriteString / Write
            if isinstance(value, dict):
                return "{" + ",".join(csharp(k) + ":" + csharp(value[k]) for k in sorted(value)) + "}"
            if isinstance(value, int):
                return str(value)
            out = []
            for c in value:  # C# iterates UTF-16 code units: split astral chars into surrogates
                for unit in ([c] if ord(c) < 0x10000 else
                             [chr(0xD800 + ((ord(c) - 0x10000) >> 10)), chr(0xDC00 + ((ord(c) - 0x10000) & 0x3FF))]):
                    esc = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t",
                           "\b": "\\b", "\f": "\\f"}.get(unit)
                    out.append(esc or (unit if " " <= unit <= "~" else "\\u%04x" % ord(unit)))
            return '"' + "".join(out) + '"'

        self.assertEqual(ee.canonical_json(payload), csharp(payload))
        expected = hashlib.sha256(csharp(payload).encode("utf-8")).hexdigest()
        self.assertEqual(ee.payload_sha256(payload), expected)
        # The defect being fixed: ensure_ascii=False yields a different digest for non-ASCII payloads.
        wrong = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False).encode("utf-8")).hexdigest()
        self.assertNotEqual(wrong, expected)

    def test_floats_bools_and_out_of_range_integers(self):
        for bad in ({"order": 1.0}, {"order": float("nan")}, {"x-a": [2**63]}, {"x-a": 1e3}):
            with self.subTest(bad=bad), self.assertRaises(EnvelopeError):
                ee.payload_sha256(bad)
        for text in ('{"a":1.0}', '{"a":1e5}', '{"a":NaN}', '{"a":Infinity}', '{"a":9223372036854775808}',
                     '{"a":"\\ud800"}', '{"bad key":1}', "[" * 40 + "]" * 40):
            with self.subTest(text=text), self.assertRaises(EnvelopeError) as ctx:
                ee.loads_strict(text)
            self.assertEqual(ctx.exception.code, "MalformedDocument")
        world = ee.world_item("cr.world.reef", order=True)
        with self.assertRaises(EnvelopeError) as ctx:
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[world])
        self.assertEqual(ctx.exception.items[0][1], "FieldTypeInvalid")

    def test_utc_rule_rejects_fractional_seconds_and_other_iso_forms(self):
        self.assertEqual(ee.parse_utc("2026-12-01T00:00:00Z").isoformat(), "2026-12-01T00:00:00+00:00")
        for bad in ("2026-12-01T00:00:00.000Z", "2026-12-01T00:00:00.123456Z", "2026-12-01T00:00:00+00:00",
                    "2026-12-01 00:00:00Z", "20261201T000000Z", "2026-12-01T00:00Z", "2026-02-30T00:00:00Z",
                    "２026-12-01T00:00:00Z", None, 0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ee.parse_utc(bad)
        ev = ee.event_item("cr.event.x", start_utc="2026-12-01T00:00:00.5Z", end_utc="2026-12-08T00:00:00Z",
                           level_ids=["cr.level.0001"])
        with self.assertRaises(EnvelopeError) as ctx:
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[ev],
                              known_level_ids=["cr.level.0001"])
        self.assertEqual(ctx.exception.items[0][1:], ("EventWindowMalformed", "startUtc"))
        # Shared calendar preview applies the same rule (no silent rounding of microseconds).
        schedule = winter()
        self.assertEqual(preview_event_window(schedule, observed_server_utc="2026-12-02T00:00:00Z"),
                         "ACTIVE_DISPLAY_PREVIEW_NO_GRANT")
        for bad in ("2026-12-02T00:00:00.999999Z", "20261202T000000Z", "2026-12-02 00:00:00Z"):
            with self.subTest(observed=bad), self.assertRaises(ValueError):
                preview_event_window(schedule, observed_server_utc=bad)

    def test_ids_references_and_order_slots(self):
        for bad in ("ab", "1abc", "a" * 81, "cr level", "cr/level", "céx"):
            self.assertFalse(ee.is_valid_id(bad), bad)
        self.assertTrue(ee.is_valid_id("a" * 80))
        reef = ee.world_item("cr.world.reef", order=1)
        cases = [
            ([reef, ee.world_item("cr.world.kelp", order=1)], (1, "DuplicateOrder")),
            ([reef, ee.world_item("bad id", order=2)], (1, "IdInvalid")),
            ([reef, ee.level_item("cr.level.1", world_id="cr.world.none", order=1, moves=20,
                                  objectives=OBJECTIVES, obstacle_ids=[])], (1, "DanglingReference")),
            ([reef, ee.level_item("cr.level.1", world_id="cr.world.reef", order=1, moves=1000,
                                  objectives=OBJECTIVES, obstacle_ids=[])], (1, "ValueOutOfRange")),
            ([reef, ee.level_item("cr.level.1", world_id="cr.world.reef", order=1, moves=20,
                                  objectives=[dict(OBJECTIVES[0], kind="Score")], obstacle_ids=[])],
             (1, "ValueOutOfRange")),
            ([reef, ee.level_item("cr.level.1", world_id="cr.world.reef", order=1, moves=20,
                                  objectives=OBJECTIVES * 5, obstacle_ids=[])], (1, "ValueOutOfRange")),
            ([reef, ee.level_item("cr.level.1", world_id="cr.world.reef", order=1, moves=20,
                                  objectives=OBJECTIVES, obstacle_ids=["obstacle.ice"] * 2)],
             (1, "DuplicateContentId")),
        ]
        for items, expected in cases:
            with self.subTest(expected=expected), self.assertRaises(EnvelopeError) as ctx:
                ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=items)
            self.assertEqual([x[:2] for x in ctx.exception.items], [expected])
        with self.assertRaises(EnvelopeError):
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[reef] * (ee.MAX_ITEMS + 1))
        with self.assertRaises(EnvelopeError):
            ee.level_item_from_draft(draft(), game_id="Coral_Rescue", order=1, goal_kinds={"g1": "CollectPiece"})

    def test_written_text_size_limit_is_engine_256_kib(self):
        def env(pad):
            items = [ee.world_item("cr.world.reef", order=1, extensions={"x-note": "a" * pad})]
            return {"schemaVersion": "1.0", "producerId": "p", "gameId": "Coral_Rescue", "items": items}

        base = len(ee.dumps(env(0)).encode("utf-8"))
        exact = ee.MAX_UTF8_BYTES - base
        text = ee.dumps(env(exact))
        self.assertEqual(len(text.encode("utf-8")), ee.MAX_UTF8_BYTES)
        built = ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=env(exact)["items"])
        ee.validate_text(ee.dumps(built), **CORAL)
        for fn in (lambda: ee.dumps(env(exact + 1)),
                   lambda: ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=env(exact + 1)["items"]),
                   lambda: ee.loads_strict(text[:-1] + "  \n")):
            with self.assertRaises(EnvelopeError) as ctx:
                fn()
            self.assertEqual(ctx.exception.code, "MalformedDocument")
        # Near-limit realistic batch: many full levels still fits and round-trips.
        levels = [ee.level_item(f"cr.level.{i:04d}", world_id="cr.world.reef", order=i + 1, moves=25,
                                objectives=OBJECTIVES, obstacle_ids=["obstacle.ice"]) for i in range(380)]
        big = ee.build_envelope(game_id="Coral_Rescue", producer_id="p",
                                items=[ee.world_item("cr.world.reef", order=1)] + levels)
        self.assertGreater(len(ee.dumps(big)), 230 * 1024)
        ee.validate_text(ee.dumps(big), **CORAL)
        with self.assertRaises(EnvelopeError):
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p",
                              items=[ee.world_item("cr.world.reef", order=1)] + levels + [
                                  ee.level_item(f"cr.level.x{i:04d}", world_id="cr.world.reef", order=400 + i,
                                                moves=25, objectives=OBJECTIVES, obstacle_ids=["obstacle.ice"])
                                  for i in range(100)])

    def test_reader_maps_deep_nesting_and_huge_integers_to_malformed(self):
        for text in ("[" * 100000 + "]" * 100000, '{"a":' + "9" * 5000 + "}", '{"a":' * 50000 + "1" + "}" * 50000):
            with self.subTest(size=len(text)), self.assertRaises(EnvelopeError) as ctx:
                ee.loads_strict(text)
            self.assertEqual(ctx.exception.code, "MalformedDocument")

    def test_receiver_allowed_kinds_reported_like_engine(self):
        reef = ee.world_item("cr.world.reef", order=1)
        lvl = ee.level_item("cr.level.0001", world_id="cr.world.reef", order=1, moves=20,
                            objectives=OBJECTIVES, obstacle_ids=[])
        with self.assertRaises(EnvelopeError) as ctx:
            ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[reef, lvl], allowed_kinds=["World"])
        self.assertEqual([x[:2] for x in ctx.exception.items], [(1, "ContentKindNotAllowed")])
        ee.build_envelope(game_id="Coral_Rescue", producer_id="p", items=[reef, lvl],
                          allowed_kinds=["World", "Level"])


class GameCompilationTests(unittest.TestCase):
    def content(self):
        return {g: [ee.world_item(g.lower().replace("_", ".") + ".world", order=1)] for g in ee.GAME_IDS}

    def test_game_ids_mirror_engine_catalog_and_factory_profiles(self):
        self.assertEqual(ee.GAME_IDS, PROFILES)
        for g in PROFILES:
            self.assertEqual(ee.game_id_for_profile(g), g)
        for bad in ("Unknown_Game", "coral_rescue", ""):
            with self.assertRaises(EnvelopeError):
                ee.game_id_for_profile(bad)

    def test_five_game_compilation_is_per_game_engine_envelopes(self):
        out = ee.compile_game_envelopes(self.content(), producer_id=ee.PRODUCER_ID)
        self.assertEqual(tuple(out), ee.GAME_IDS)
        for game, env in out.items():
            self.assertEqual(list(env), ["schemaVersion", "producerId", "gameId", "items"])
            self.assertEqual(env["schemaVersion"], "1.0")
            self.assertEqual(env["gameId"], game)
            text = ee.dumps(env)
            self.assertTrue(text.isascii())
            ee.validate_text(text, game_id=game)
            for other in ee.GAME_IDS:
                if other != game:
                    with self.assertRaises(EnvelopeError):
                        ee.validate_text(text, game_id=other)
        self.assertEqual(out, ee.compile_game_envelopes(self.content(), producer_id=ee.PRODUCER_ID))

    def test_compilation_per_game_allowed_kinds(self):
        content = self.content()
        out = ee.compile_game_envelopes(content, producer_id=ee.PRODUCER_ID,
                                        allowed_kinds={"Wonder_Pop": ["World"]})
        self.assertEqual(set(out), set(ee.GAME_IDS))
        with self.assertRaises(EnvelopeError) as ctx:
            ee.compile_game_envelopes(content, producer_id=ee.PRODUCER_ID,
                                      allowed_kinds={"Wonder_Pop": ["Level", "Event"]})
        self.assertEqual(ctx.exception.items[0][1], "ContentKindNotAllowed")
        with self.assertRaises(EnvelopeError):
            ee.compile_game_envelopes(content, producer_id=ee.PRODUCER_ID, allowed_kinds={"Nope_Game": ["World"]})

    def test_compilation_fails_closed(self):
        content = self.content()
        missing = dict(content)
        del missing["Wonder_Pop"]
        for bad in (missing, dict(content, Extra_Game=[]), dict(content, Wonder_Pop=[])):
            with self.assertRaises(EnvelopeError):
                ee.compile_game_envelopes(bad, producer_id=ee.PRODUCER_ID)
        poisoned = copy.deepcopy(content)
        poisoned["Dino_Islands"][0]["payload"]["x-offerId"] = "o"
        with self.assertRaises(EnvelopeError):
            ee.compile_game_envelopes(poisoned, producer_id=ee.PRODUCER_ID)


if __name__ == "__main__":
    unittest.main()

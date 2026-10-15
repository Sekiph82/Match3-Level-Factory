"""Strict neutral LevelDraft prototype serialization and donor adapters."""

from __future__ import annotations

import hashlib
import json
from typing import Any

PROFILE_IDS = {
    "Coral_Rescue", "Garage_Legends", "Dino_Islands",
    "The_Fractured_Realms", "Wonder_Pop",
}
TOP_LEVEL_KEYS = {
    "draftVersion", "validationStatus", "gameProfileId", "profileVersion", "worldId", "chapterId", "levelId",
    "releaseChannel", "platform", "locale", "seed", "width", "height",
    "minEngineVersion", "maxEngineVersion",
    "layers", "activeMask", "moveBudget", "cells", "goals", "engineSchemaVersion",
    "timedMode", "timeLimitSeconds", "oneStarThreshold", "twoStarThreshold", "threeStarThreshold",
    "difficultyLabel", "editorHintKey",
    "sourceRepository", "sourceRevision", "sourceKind",
}
CELL_KEYS = {
    "row", "column", "layer", "active", "locked", "contentId", "obstacleId",
    "obstacleDurability", "lockDurability", "specialId",
}
GOAL_KEYS = {"goalId", "targetId", "targetCount"}


class DraftError(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DraftError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 2_000_000:
        raise DraftError("JSON input must be text no larger than 2 MB")
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=lambda value: (_ for _ in ()).throw(DraftError(f"invalid number: {value}")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise DraftError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DraftError("draft root must be an object")
    validate(value)
    return canonicalize(value)


def validate(draft: dict[str, Any]) -> None:
    _keys(draft, TOP_LEVEL_KEYS, "draft")
    if draft.get("draftVersion") != 1:
        raise DraftError("draftVersion must be 1")
    if draft.get("validationStatus") != "PROTOTYPE_ONLY":
        raise DraftError("validationStatus must be PROTOTYPE_ONLY until the Engine gate is accepted")
    if draft.get("gameProfileId") not in PROFILE_IDS:
        raise DraftError("unknown gameProfileId")
    if _bounded_int(draft.get("profileVersion"), 1, 1, "profileVersion") != 1:
        raise DraftError("unsupported profileVersion")
    for name in ("worldId", "chapterId", "levelId"):
        value = draft.get(name)
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(not (ch.isalnum() or ch in "._-") or ord(ch) > 127 for ch in value):
            raise DraftError(f"{name} must be a stable identifier")
    if draft.get("releaseChannel") not in {"local", "development", "staging"}:
        raise DraftError("releaseChannel is not available before ENG-M24")
    if draft.get("platform") not in {"windows-editor", "windows", "android", "ios", "webgl"}:
        raise DraftError("unknown platform")
    import re
    if not isinstance(draft.get("locale"), str) or re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", draft["locale"]) is None:
        raise DraftError("locale must be a BCP-47-style language tag")
    if draft.get("minEngineVersion") is not None or draft.get("maxEngineVersion") is not None:
        raise DraftError("Engine version constraints are unavailable until ENG-M24")
    width = _bounded_int(draft.get("width"), 1, 32, "width")
    height = _bounded_int(draft.get("height"), 1, 32, "height")
    layers = _bounded_int(draft.get("layers"), 1, 4, "layers")
    _bounded_int(draft.get("seed"), 0, 2**63 - 1, "seed")
    _bounded_int(draft.get("moveBudget"), 1, 999, "moveBudget")
    timed = draft.get("timedMode")
    if type(timed) is not bool:
        raise DraftError("timedMode must be boolean")
    seconds = _bounded_int(draft.get("timeLimitSeconds"), 0, 3600, "timeLimitSeconds")
    if (timed and seconds < 1) or (not timed and seconds != 0):
        raise DraftError("timeLimitSeconds must be 1..3600 for timed levels and 0 otherwise")
    one = _bounded_int(draft.get("oneStarThreshold"), 0, 99999, "oneStarThreshold")
    two = _bounded_int(draft.get("twoStarThreshold"), one, 99999, "twoStarThreshold")
    _bounded_int(draft.get("threeStarThreshold"), two, 99999, "threeStarThreshold")
    for name in ("difficultyLabel", "editorHintKey"):
        value = draft.get(name)
        if name == "editorHintKey" and value is None:
            continue
        if not isinstance(value, str) or not value or len(value) > 128 or any(not (ch.isalnum() or ch in "._-") or ord(ch) > 127 for ch in value):
            raise DraftError(f"{name} must be a stable localization key")
    if draft.get("engineSchemaVersion") is not None:
        raise DraftError("engineSchemaVersion must remain null while no accepted final Engine schema is available")

    mask = draft.get("activeMask")
    expected = width * height * layers
    if not isinstance(mask, list) or len(mask) != expected or any(type(item) is not bool for item in mask):
        raise DraftError(f"activeMask must contain exactly {expected} booleans")
    cells = draft.get("cells")
    if not isinstance(cells, list) or len(cells) != expected:
        raise DraftError(f"cells must contain exactly {expected} entries, including holes")
    seen = set()
    for cell in cells:
        if not isinstance(cell, dict):
            raise DraftError("each cell must be an object")
        _keys(cell, CELL_KEYS, "cell")
        row = _bounded_int(cell.get("row"), 0, height - 1, "cell.row")
        column = _bounded_int(cell.get("column"), 0, width - 1, "cell.column")
        layer = _bounded_int(cell.get("layer"), 0, layers - 1, "cell.layer")
        key = (layer, row, column)
        if key in seen:
            raise DraftError(f"duplicate cell coordinate {key}")
        seen.add(key)
        index = (layer * height + row) * width + column
        if type(cell.get("active")) is not bool or cell["active"] != mask[index]:
            raise DraftError(f"activeMask disagrees with cell {key}")
        if type(cell.get("locked")) is not bool:
            raise DraftError(f"cell {key} locked must be boolean")
        if cell["active"] and not isinstance(cell.get("contentId"), str) and not isinstance(cell.get("obstacleId"), str):
            raise DraftError(f"active cell {key} requires contentId or obstacleId")
        if not cell["active"] and (cell.get("contentId") is not None or cell.get("obstacleId") is not None):
            raise DraftError(f"hole {key} cannot carry content or an obstacle")
        _bounded_int(cell.get("obstacleDurability"), 0, 99, "obstacleDurability")
        _bounded_int(cell.get("lockDurability"), 0, 99, "lockDurability")
        for name in ("contentId", "obstacleId", "specialId"):
            value = cell.get(name)
            if value is not None and (not isinstance(value, str) or not value or len(value) > 128):
                raise DraftError(f"cell {key} has invalid {name}")

    goals = draft.get("goals")
    if not isinstance(goals, list) or not goals or len(goals) > 32:
        raise DraftError("goals must contain 1..32 entries")
    goal_ids = set()
    for goal in goals:
        if not isinstance(goal, dict):
            raise DraftError("each goal must be an object")
        _keys(goal, GOAL_KEYS, "goal")
        goal_id = goal.get("goalId")
        target_id = goal.get("targetId")
        if not isinstance(goal_id, str) or not goal_id or len(goal_id) > 128 or goal_id in goal_ids:
            raise DraftError("goal IDs must be present, unique strings")
        if not isinstance(target_id, str) or not target_id or len(target_id) > 128:
            raise DraftError("goal targetId must be a nonempty string")
        goal_ids.add(goal_id)
        _bounded_int(goal.get("targetCount"), 1, 99999, "goal.targetCount")

    for name in ("sourceRepository", "sourceRevision", "sourceKind"):
        value = draft.get(name)
        if value is not None and (not isinstance(value, str) or len(value) > 256):
            raise DraftError(f"invalid {name}")


def _keys(value: dict, allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown:
        raise DraftError(f"unknown {context} fields: {', '.join(sorted(unknown))}")
    if missing:
        raise DraftError(f"missing {context} fields: {', '.join(sorted(missing))}")


def _bounded_int(value, minimum: int, maximum: int, name: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DraftError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def canonicalize(draft: dict[str, Any]) -> dict[str, Any]:
    result = {key: draft.get(key) for key in (
        "draftVersion", "validationStatus", "gameProfileId", "profileVersion", "worldId", "chapterId", "levelId",
        "releaseChannel", "platform", "locale", "minEngineVersion", "maxEngineVersion", "seed", "width", "height",
        "layers", "activeMask", "moveBudget", "timedMode", "timeLimitSeconds",
        "oneStarThreshold", "twoStarThreshold", "threeStarThreshold", "difficultyLabel", "editorHintKey",
        "cells", "goals", "engineSchemaVersion",
        "sourceRepository", "sourceRevision", "sourceKind",
    )}
    result["cells"] = sorted(result["cells"], key=lambda cell: (cell["row"], cell["column"], cell["layer"]))
    result["goals"] = sorted(result["goals"], key=lambda goal: goal["goalId"])
    return result


def dumps_canonical(draft: dict[str, Any], *, pretty: bool = False) -> str:
    validate(draft)
    canonical = canonicalize(draft)
    if pretty:
        return json.dumps(canonical, ensure_ascii=False, indent=2) + "\n"
    return json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))


def sha256(draft: dict[str, Any]) -> str:
    return hashlib.sha256(dumps_canonical(draft).encode("utf-8")).hexdigest()


def from_ultragem(candidate: dict[str, Any], *, profile_id: str = "Coral_Rescue", move_budget: int = 20) -> dict[str, Any]:
    board = candidate["initialBoard"]
    rows, columns = board["rows"], board["columns"]
    cells = []
    mask = []
    for item in sorted(board["cells"], key=lambda value: (value["row"], value["column"])):
        cell_type, color, status = item["type"], item["color"], item["status"]
        active = cell_type != -1
        mask.append(active)
        if not active:
            content_id = obstacle_id = special_id = None
            lock_durability = obstacle_durability = 0
        elif cell_type == 0 and status > 0:
            content_id = None
            obstacle_id = "ultragem.double_lock" if status == 2 else "ultragem.locked_empty"
            special_id = None
            lock_durability = 0
            obstacle_durability = status
        elif cell_type == 0:
            content_id = "ultragem.spawn_random"
            obstacle_id = special_id = None
            lock_durability = obstacle_durability = 0
        else:
            content_id = f"ultragem.color.{color}"
            obstacle_id = None
            special_id = {1: None, 2: "ultragem.stripe_h", 3: "ultragem.stripe_v", 4: "ultragem.bomb", 5: "ultragem.zapper"}.get(cell_type)
            if cell_type not in (1, 2, 3, 4, 5):
                raise DraftError(f"unsupported UltraGem field type: {cell_type}")
            lock_durability = max(0, status)
            obstacle_durability = 0
        cells.append({
            "row": item["row"], "column": item["column"], "layer": 0,
            "active": active, "locked": status > 0 and cell_type > 0,
            "contentId": content_id, "obstacleId": obstacle_id,
            "obstacleDurability": obstacle_durability, "lockDurability": lock_durability,
            "specialId": special_id,
        })
    draft = {
        "draftVersion": 1, "validationStatus": "PROTOTYPE_ONLY", "gameProfileId": profile_id,
        "seed": candidate["seed"], "width": columns, "height": rows, "layers": 1,
        "activeMask": mask, "moveBudget": move_budget, "cells": cells,
        "goals": [{"goalId": "goal.primary", "targetId": "ultragem.score", "targetCount": 1}],
        "engineSchemaVersion": None, "sourceRepository": "JohannesBuchner/ultragem",
        "profileVersion": 1, "worldId": "world.prototype", "chapterId": "chapter.prototype",
        "levelId": f"level.seed-{candidate['seed']}", "releaseChannel": "local", "platform": "windows-editor",
        "locale": "en", "minEngineVersion": None, "maxEngineVersion": None,
        "timedMode": False, "timeLimitSeconds": 0, "oneStarThreshold": 1, "twoStarThreshold": 2,
        "threeStarThreshold": 3, "difficultyLabel": "difficulty.unrated", "editorHintKey": None,
        "sourceRevision": "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12", "sourceKind": "UltraGemCandidate",
    }
    validate(draft)
    return canonicalize(draft)

"""Render persisted Factory-local sample LevelDrafts as neutral PNG previews.

These board-data illustrations are not Unity screenshots or gameplay evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

import leveldraft
from factory_local_authoring import PALETTE, SOURCE_KIND

COLORS = {
    "Blue": (59, 130, 246), "Green": (34, 197, 94), "Orange": (249, 115, 22),
    "Purple": (168, 85, 247), "White": (226, 232, 240), "Yellow": (234, 179, 8),
}
BACKGROUND = (15, 23, 42)
EMPTY = (51, 65, 85)
INK = (241, 245, 249)
BOARD_PADDING = 24
CELL_SIZE = 72
HEADER_HEIGHT = 178
MAX_PNG_BYTES = 1_000_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                        indent=2 if pretty else None, separators=None if pretty else (",", ":")) + "\n").encode("utf-8")


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def load_verified_draft(path: Path, expected_sha256: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("source LevelDraft exceeds the 1 MB input limit")
    try:
        draft = leveldraft.loads_strict(raw.decode("utf-8"))
        leveldraft.validate(draft)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ValueError(f"source LevelDraft is invalid: {exc}") from exc
    if draft.get("sourceKind") != SOURCE_KIND:
        raise ValueError("source is not a Factory-original local sample board")
    actual = leveldraft.sha256(draft)
    if not isinstance(expected_sha256, str) or actual != expected_sha256:
        raise ValueError("source draft SHA-256 does not match the expected provenance")
    width, height = draft.get("width"), draft.get("height")
    if type(width) is not int or type(height) is not int or not 6 <= width <= 12 or not 6 <= height <= 12:
        raise ValueError("unsupported board dimensions")
    if len(draft.get("activeMask", [])) != width * height:
        raise ValueError("activeMask dimensions do not match board")
    seen = set()
    for cell in draft.get("cells", []):
        row, col = cell.get("row"), cell.get("column")
        if type(row) is not int or type(col) is not int or not (0 <= row < height and 0 <= col < width):
            raise ValueError("cell coordinate is outside board dimensions")
        coord = row, col
        if coord in seen:
            raise ValueError("duplicate cell coordinate")
        seen.add(coord)
        if cell.get("contentId") not in PALETTE:
            raise ValueError("unsupported cell color id")
        if cell.get("obstacleId") is not None or cell.get("specialId") is not None or cell.get("locked"):
            raise ValueError("sample renderer does not accept unverified special or obstacle mechanics")
    if len(seen) != width * height:
        raise ValueError("sample board must provide one explicit cell per coordinate")
    for index, cell in enumerate(sorted(draft["cells"], key=lambda c: (c["row"], c["column"]))):
        if draft["activeMask"][index] != bool(cell["active"]):
            raise ValueError("activeMask and cell active state disagree")
    return draft, raw


def render_verified_draft(source_path: Path, expected_sha256: str, output_path: Path) -> dict[str, Any]:
    draft, raw = load_verified_draft(source_path, expected_sha256)
    width, height = draft["width"], draft["height"]
    image = Image.new("RGB", (BOARD_PADDING * 2 + width * CELL_SIZE,
                               HEADER_HEIGHT + BOARD_PADDING * 2 + height * CELL_SIZE), BACKGROUND)
    draw = ImageDraw.Draw(image)
    profile = draft["gameProfileId"]
    draw.text((BOARD_PADDING, 18), f"{profile} · {draft['levelId']}", fill=INK, font=_font(23))
    draw.text((BOARD_PADDING, 53), f"Seed {draft['seed']}  |  {width} x {height}  |  {draft['sourceKind']}",
              fill=(203, 213, 225), font=_font(14))
    draw.text((BOARD_PADDING, 78), f"Draft SHA-256  {expected_sha256}", fill=(148, 163, 184), font=_font(12))
    draw.text((BOARD_PADDING, 101), "LOCAL PREVIEW ONLY  |  ENGINE NOT VERIFIED", fill=(251, 191, 36), font=_font(18))
    draw.text((BOARD_PADDING, 133), "Studio sample palette · active cells shown in color · inactive cells shown slate",
              fill=(203, 213, 225), font=_font(12))
    cells = {(cell["row"], cell["column"]): cell for cell in draft["cells"]}
    for row in range(height):
        for col in range(width):
            x = BOARD_PADDING + col * CELL_SIZE
            y = HEADER_HEIGHT + row * CELL_SIZE
            cell = cells[(row, col)]
            active = bool(cell["active"])
            color = COLORS[cell["contentId"]] if active else EMPTY
            draw.rounded_rectangle((x + 3, y + 3, x + CELL_SIZE - 3, y + CELL_SIZE - 3),
                                   radius=12, fill=color, outline=(148, 163, 184), width=2)
            draw.ellipse((x + 21, y + 21, x + CELL_SIZE - 21, y + CELL_SIZE - 21),
                         fill=tuple(min(255, c + 35) for c in color), outline=(255, 255, 255), width=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError("refusing to overwrite an existing preview PNG")
    image.save(output_path, format="PNG", optimize=False, compress_level=9)
    png = output_path.read_bytes()
    if len(png) > MAX_PNG_BYTES:
        output_path.unlink()
        raise ValueError("rendered PNG exceeds the 1 MB output limit")
    return {"sourcePath": source_path.as_posix(), "sourceFileSha256": _sha(raw),
            "draftSha256": expected_sha256, "pngPath": output_path.as_posix(),
            "pngSha256": _sha(png), "pngBytes": len(png), "gameProfileId": profile,
            "levelId": draft["levelId"], "seed": draft["seed"],
            "grid": f"{width}x{height}", "sourceKind": SOURCE_KIND,
            "label": "LOCAL PREVIEW ONLY | ENGINE NOT VERIFIED"}


def render_contact_sheet(images: list[Path], output_path: Path) -> dict[str, Any]:
    if not images or len(images) > 10:
        raise ValueError("contact sheet accepts 1 to 10 verified individual previews")
    opened = [Image.open(path).convert("RGB") for path in images]
    tile_w = max(im.width for im in opened)
    tile_h = max(im.height for im in opened)
    columns = 2
    rows = (len(opened) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_w, rows * tile_h), BACKGROUND)
    for index, image in enumerate(opened):
        sheet.paste(image, ((index % columns) * tile_w, (index // columns) * tile_h))
    if output_path.exists():
        raise FileExistsError("refusing to overwrite an existing contact sheet")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=False, compress_level=9)
    raw = output_path.read_bytes()
    if len(raw) > 10_000_000:
        output_path.unlink()
        raise ValueError("contact sheet exceeds the 10 MB output limit")
    return {"pngPath": output_path.as_posix(), "pngSha256": _sha(raw), "pngBytes": len(raw),
            "imageCount": len(images), "label": "LOCAL PREVIEW ONLY | ENGINE NOT VERIFIED"}


def build_visual_evidence(run_dirs: Path | list[Path], output_dir: Path) -> dict[str, Any]:
    if isinstance(run_dirs, Path):
        run_dirs = [run_dirs]
    if not run_dirs or len(run_dirs) > 2:
        raise ValueError("visual evidence accepts one or two bounded local authoring runs")
    entries = []
    checkpoints = []
    for run_dir in run_dirs:
        checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
        checkpoints.append(checkpoint)
        for record in checkpoint.get("records", []):
            if record["status"] != "LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY":
                continue
            source = run_dir / record["path"]
            preview = output_dir / (record["profileId"] + "-" + f"{record['seed']}-{record['draftSha256'][:12]}.png")
            entries.append(render_verified_draft(source, record["draftSha256"], preview))
    if len(entries) < 5:
        raise ValueError("visual evidence requires at least five accepted persisted sample boards")
    contact = render_contact_sheet([Path(item["pngPath"]) for item in entries], output_dir / "contact-sheet.png")
    manifest = {"manifestVersion": 1, "classification": "BOARD_DATA_PREVIEWS_NOT_UNITY_SCREENSHOTS",
                "sourceRevision": checkpoints[0]["sourceRevision"],
                "configurationSha256": [c["configurationSha256"] for c in checkpoints],
                "engineStatus": "BLOCKED_ENG_M24", "engineQualifiedCampaignLevels": 0,
                "images": entries, "contactSheet": contact}
    manifest_path = output_dir / "visual-manifest.json"
    if manifest_path.exists():
        raise FileExistsError("refusing to overwrite visual manifest")
    manifest_path.write_bytes(_json_bytes(manifest, pretty=True))
    return manifest

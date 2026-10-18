"""LFX-M07-005: static editor-only Unity assembly firewall preflight.

Reads real source and asmdef inventory without modifying Unity. This is not a
Windows Player build or proof that scenes/Addressables cannot ship assets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROTECTED_ROOTS = ("Assets/Match3", "Assets/Match3Factory")
MAX_ASMDEFS = 256
MAX_SCRIPTS = 20000
MAX_ASMDEF_BYTES = 100_000


def _protected(path: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in PROTECTED_ROOTS)


def _file_path(path: str) -> str:
    if (not isinstance(path, str) or not path.startswith("Assets/") or "\\" in path
        or path.startswith("/") or "//" in path or any(x in (".", "..") for x in path.split("/"))):
        raise ValueError("expected safe Assets-relative POSIX path")
    return path


def inspect_assembly_firewall(asmdefs: dict[str, str], asset_paths: list[str]) -> dict[str, Any]:
    if (not isinstance(asmdefs, dict) or not isinstance(asset_paths, list)
        or not 1 <= len(asmdefs) <= MAX_ASMDEFS or len(asset_paths) > MAX_SCRIPTS
        or len(asset_paths) != len(set(asset_paths))):
        raise ValueError("bounded unique assembly/source inventory required")
    names = {}
    roots = {}
    problems = []
    for path, raw in sorted(asmdefs.items()):
        _file_path(path)
        if not path.endswith(".asmdef") or not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_ASMDEF_BYTES:
            raise ValueError("invalid asmdef path/payload")
        try:
            definition = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"malformed asmdef: {path}") from exc
        if not isinstance(definition, dict) or not isinstance(definition.get("name"), str):
            raise ValueError("asmdef must declare name")
        name = definition["name"]
        if name in names:
            raise ValueError("duplicate assembly name")
        names[name] = (path, definition)
        roots[path.rsplit("/", 1)[0]] = name
    for name, (path, definition) in names.items():
        if not _protected(path):
            continue
        platforms = definition.get("includePlatforms", [])
        constraints = definition.get("defineConstraints", [])
        if not isinstance(platforms, list) or not isinstance(constraints, list):
            raise ValueError("invalid asmdef inclusion declarations")
        editor_only = platforms == ["Editor"] or (
            not platforms and "UNITY_EDITOR" in constraints)
        if not editor_only:
            problems.append({"code": "PROTECTED_ASSEMBLY_COMPILABLE_IN_PLAYER", "assembly": name})
        if definition.get("autoReferenced", True) and "Tests" in path:
            problems.append({"code": "TEST_ASSEMBLY_AUTO_REFERENCED", "assembly": name})
    checked_scripts = 0
    for path in sorted(asset_paths):
        _file_path(path)
        if not path.endswith(".cs") or not _protected(path):
            continue
        checked_scripts += 1
        parts = path.split("/")[:-1]
        owner = None
        for length in range(len(parts), 1, -1):
            candidate = "/".join(parts[:length])
            if candidate in roots:
                owner = roots[candidate]
                break
        if owner is None:
            problems.append({"code": "UNPROTECTED_EDITOR_SCRIPT", "script": path})
        elif not _protected(names[owner][0]):
            problems.append({"code": "SCRIPT_BELONGS_TO_RUNTIME_ASSEMBLY", "script": path})
    for name, (path, definition) in names.items():
        if _protected(path):
            continue
        platforms = definition.get("includePlatforms", [])
        constraints = definition.get("defineConstraints", [])
        is_editor = platforms == ["Editor"] or "UNITY_EDITOR" in constraints
        if not is_editor:
            for reference in definition.get("references", []):
                if reference in names and _protected(names[reference][0]):
                    problems.append({"code": "RUNTIME_ASSEMBLY_REFERENCES_EDITOR", "assembly": name, "reference": reference})
    return {
        "resultStatus": "STATIC_FIREWALL_BLOCKED" if problems else "STATIC_FIREWALL_CLEAN_NOT_PLAYER_TESTED",
        "engineStatus": "BLOCKED_ENG_M24",
        "protectedAssemblyCount": sum(_protected(path) for path, _ in names.values()),
        "protectedScriptCount": checked_scripts,
        "findings": problems,
        "actualWindowsPlayerBuildPerformed": False,
        "actualBuildBinaryInspected": False,
        "releaseAuthorized": False,
    }


def inspect_local_project(repo_root: Path) -> dict[str, Any]:
    """Read-only, no-symlink-walk project scan, accepts only existing roots."""
    if not repo_root.is_dir() or repo_root.is_symlink():
        raise ValueError("local Unity root directory required")
    asset_root = repo_root / "Assets"
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise ValueError("Assets directory missing")
    paths = []
    defs = {}
    # Only scan the two explicitly protected trees, not user/private folders.
    for root in PROTECTED_ROOTS:
        directory = repo_root / root
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f"required Unity asset folder missing: {root}")
        for p in sorted(directory.rglob("*")):
            if p.is_symlink():
                raise ValueError("Unity source symlink cannot be audited")
            if not p.is_file():
                continue
            rel = p.relative_to(repo_root).as_posix()
            if p.suffix == ".asmdef":
                defs[rel] = p.read_text(encoding="utf-8")
            elif p.suffix == ".cs":
                paths.append(rel)
    # Also inspect unrelated runtime asmdefs. A consumer assembly must not
    # reference an editor-only Factory assembly by name.
    for p in sorted(asset_root.rglob("*.asmdef")):
        if p.is_symlink():
            raise ValueError("Unity assembly symlink cannot be audited")
        rel = p.relative_to(repo_root).as_posix()
        if rel not in defs:
            defs[rel] = p.read_text(encoding="utf-8")
        if len(defs) > MAX_ASMDEFS:
            raise ValueError("assembly inventory exceeds bounded scan")
    return inspect_assembly_firewall(defs, paths)

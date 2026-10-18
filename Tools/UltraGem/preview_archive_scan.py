"""Bounded, in-memory inspection of prototype content ZIP bytes (LFX-M09-010).

This is a *pre-release file-integrity check*, NOT authorization to distribute.
Never extracts to disk or follows paths. It preserves all final signing,
content-rights, user acceptance and MATCH3_ENGINE gates.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

from content_exclusion import validate_preview_file_inventory

MAX_ARCHIVE_BYTES = 32_000_000
MAX_MEMBER_BYTES = 8_000_000
MAX_TOTAL_UNCOMPRESSED = 32_000_000
MAX_EXPANSION_RATIO = 100
CHUNK = 65_536
_ALLOWED_ZIP_METHODS = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
_FORBIDDEN_CONTENT = re.compile(rb'''(?i)(?:BEGIN [\w ]*PRIVATE KEY|[\"'](?:api[_-]?key|secret|password|private[_-]?key|access[_-]?token)[\"']\s*:|(?:api[_-]?key|password)\s*[=:]|bearer\s+[a-z0-9._-]{10,})''')


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'duplicate JSON property: {key}')
        obj[key] = value
    return obj


def _check_actual_bytes(path: str, data: bytes, kind: str) -> None:
    if not data or _FORBIDDEN_CONTENT.search(data):
        raise ValueError('empty or credentials-like content in staged file')
    if kind in {'LEVEL_JSON', 'LOCALIZATION_JSON'}:
        if not path.lower().endswith('.json'):
            raise ValueError('invalid JSON filename')
        try:
            parsed = json.loads(data.decode('utf-8'), object_pairs_hook=_no_duplicate_keys)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('invalid JSON payload') from exc
        if not isinstance(parsed, (dict, list)):
            raise ValueError('content JSON must be object or array')
    elif kind == 'MEDIA':
        name = path.lower()
        if name.endswith('.png'):
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or b'IEND' not in data[-32:]:
                raise ValueError('invalid PNG byte signature/trailer')
        elif name.endswith('.webp'):
            if len(data) < 16 or data[:4] != b'RIFF' or data[8:12] != b'WEBP':
                raise ValueError('invalid WebP byte signature')
            if int.from_bytes(data[4:8], 'little') + 8 != len(data):
                raise ValueError('WebP size mismatch')
        elif name.endswith('.svg'):
            if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                raise ValueError('SVG entities and doctypes forbidden')
            try:
                root = ET.fromstring(data)
            except ET.ParseError as exc:
                raise ValueError('invalid SVG XML') from exc
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                raise ValueError('not a rooted SVG')
            for element in root.iter():
                tag = element.tag.split('}')[-1]
                if tag in {'script', 'foreignObject', 'image', 'use', 'animate', 'set'}:
                    raise ValueError('active or external SVG content forbidden')
                for attribute, value in element.attrib.items():
                    a = attribute.split('}')[-1].lower()
                    if a.startswith('on') or a in {'href', 'src'} or 'url(' in value.lower():
                        raise ValueError('SVG event, link or referenced content forbidden')
        else:
            raise ValueError('media format is not on the allowlist')
    else:
        raise ValueError('unrecognized inventory kind')


def scan_preview_archive(archive_bytes: bytes, inventory: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate declared inventory against every real ZIP entry, without writing.

    Any rejection aborts the *entire* archive, never reporting partial PASS.
    File rights are declarations; even a green result needs legal signoff.
    """
    if type(archive_bytes) is not bytes or not 1 <= len(archive_bytes) <= MAX_ARCHIVE_BYTES:
        raise ValueError('bounded ZIP byte input is required')
    screen = validate_preview_file_inventory(inventory)
    if screen['denied']:
        raise ValueError('release inventory has forbidden files or rights')
    declared = {entry['path']: entry for entry in screen['acceptedForFurtherInspection']}
    if not declared:
        raise ValueError('empty ZIP inventories are not eligible')
    verified = []
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            info = archive.infolist()
            if not 1 <= len(info) <= 256 or any(member.is_dir() for member in info):
                raise ValueError('ZIP must contain only 1..256 regular files')
            entries = {m.filename: m for m in info}
            if len(entries) != len(info) or set(entries) != set(declared):
                raise ValueError('ZIP entry names mismatch declared inventory or duplicate')
            total = 0
            for path in sorted(declared):
                member = entries[path]
                # Unix ZIP entries may encode links/devices: never extract/follow.
                mode = (member.external_attr >> 16) & 0xffff
                if (member.create_system == 3 and stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                    raise ValueError('ZIP symbolic link or nonregular entry forbidden')
                if member.flag_bits & 1 or member.compress_type not in _ALLOWED_ZIP_METHODS:
                    raise ValueError('encrypted or unsupported ZIP member')
                if member.file_size <= 0 or member.file_size > MAX_MEMBER_BYTES:
                    raise ValueError('ZIP member uncompressed byte limit exceeded')
                if member.compress_size == 0 or member.file_size > MAX_EXPANSION_RATIO * member.compress_size:
                    raise ValueError('ZIP decompression ratio exceeds budget')
                total += member.file_size
                if total > MAX_TOTAL_UNCOMPRESSED:
                    raise ValueError('ZIP uncompressed total exceeds budget')
                entry = declared[path]
                if entry['sizeBytes'] != member.file_size:
                    raise ValueError('ZIP member length differs from evidence manifest')
                digest = hashlib.sha256()
                buffer = bytearray()
                with archive.open(member) as stream:
                    while chunk := stream.read(CHUNK):
                        digest.update(chunk)
                        buffer.extend(chunk)
                        if len(buffer) > MAX_MEMBER_BYTES:
                            raise ValueError('ZIP member decompression over budget')
                if len(buffer) != member.file_size or digest.hexdigest() != entry['sha256']:
                    raise ValueError('ZIP member bytes differ from evidence manifest')
                _check_actual_bytes(path, bytes(buffer), entry['kind'])
                verified.append({'path': path, 'sha256': digest.hexdigest(), 'sizeBytes': len(buffer)})
    except (zipfile.BadZipFile, EOFError, RuntimeError, OSError) as exc:
        raise ValueError('invalid, truncated or corrupt ZIP archive') from exc
    return {
        'resultStatus': 'PROTOTYPE_ARCHIVE_BYTES_VERIFIED_ONLY',
        'engineStatus': 'BLOCKED_ENG_M24',
        'runtimePackInspected': True,
        'archiveSha256': hashlib.sha256(archive_bytes).hexdigest(),
        'fileCount': len(verified),
        'verifiedFiles': verified,
        'legalRightsIndependentlyVerified': False,
        'engineSchemaVerified': False,
        'signedReleaseVerified': False,
        'productionReleaseAuthorized': False,
        'remainingGates': ['LICENSE_REVIEW', 'ENG_M24', 'SIGNED_PACK', 'OWNER_APPROVAL'],
    }

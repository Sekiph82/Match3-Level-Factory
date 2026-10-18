"""LFX-M07-008: inspect raw NUnit/Python bytes and issue reproducible QA receipts.

This constructs a bounded, local, reviewable manifest. It NEVER uploads,
executes tests, authenticates a reviewer, or declares official Factory PASS.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from xml.etree import ElementTree as ET

MAX_ARTIFACTS = 32
MAX_ARTIFACT_BYTES = 1_000_000
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,159}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_REDACTION = re.compile(
    rb"(?i)(?:authorization\s*:\s*bearer\s+\S+|"
    rb"-----BEGIN\s+(?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\b(?:api[_-]?key|client[_-]?secret)\s*[:=]\s*['\"]?[^\s,'\"]{8,})"
)


def parse_nunit_xml(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("bounded raw NUnit XML required")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("DTD and entity expansion forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("invalid NUnit XML") from exc
    if root.tag != "test-run":
        raise ValueError("not a NUnit test-run")
    try:
        total, passed, failed, skipped, inconclusive = (
            int(root.attrib[k]) for k in ("total", "passed", "failed", "skipped", "inconclusive")
        )
    except (ValueError, KeyError) as exc:
        raise ValueError("NUnit totals missing or malformed") from exc
    if not 0 < total <= 100000 or min(passed, failed, skipped, inconclusive) < 0:
        raise ValueError("out-of-range NUnit counts")
    if passed + failed + skipped + inconclusive != total:
        raise ValueError("NUnit test-run totals disagree")
    cases = root.findall(".//test-case")
    if len(cases) != total:
        raise ValueError("NUnit case count differs from summary")
    if not all(case.get("result") in ("Passed", "Failed", "Skipped", "Inconclusive")
               for case in cases):
        raise ValueError("invalid case result")
    case_count = {
        status: sum(case.get("result") == label for case in cases)
        for status, label in (("passed", "Passed"), ("failed", "Failed"),
                              ("skipped", "Skipped"), ("inconclusive", "Inconclusive"))
    }
    if case_count != {"passed": passed, "failed": failed,
                      "skipped": skipped, "inconclusive": inconclusive}:
        raise ValueError("NUnit summary does not match test cases")
    status = "SCOPED_FAIL" if failed else "SCOPED_PARTIAL" if skipped or inconclusive else "SCOPED_PASS"
    return {"type": "NUNIT_XML", "scopeStatus": status, "total": total,
            "passed": passed, "failed": failed, "skipped": skipped,
            "inconclusive": inconclusive, "independentAuditPass": False}


def parse_python_unittest_log(raw: bytes, *, excluded_tests: int) -> dict[str, Any]:
    if type(raw) is not bytes or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("bounded Python unittest log required")
    if type(excluded_tests) is not int or not 0 <= excluded_tests <= 100000:
        raise ValueError("excluded test count must be explicit")
    try:
        log = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("log must be UTF-8") from exc
    match = list(re.finditer(r"(?m)^Ran (\d+) tests? in ([0-9]+(?:\.[0-9]+)?)s\s*$", log))
    if len(match) != 1:
        return {"type": "PYTHON_UNITTEST_LOG", "scopeStatus": "UNKNOWN_MISSING_TEST_SUMMARY",
                "excludedTests": excluded_tests, "independentAuditPass": False}
    total = int(match[0].group(1))
    if not 0 < total <= 100000:
        raise ValueError("invalid unittest count")
    tail = log[match[0].end():].strip()
    if re.fullmatch(r"OK(?: \(skipped=(\d+)\))?", tail):
        skipped_match = re.search(r"skipped=(\d+)", tail)
        skipped = int(skipped_match.group(1)) if skipped_match else 0
        if skipped > total:
            raise ValueError("invalid skip count")
        status = "SCOPED_PARTIAL" if skipped else "SCOPED_PASS"
    elif tail.startswith("FAILED ("):
        skipped = None
        status = "SCOPED_FAIL"
    else:
        skipped = None
        status = "UNKNOWN_INCOMPLETE_LOG"
    return {
        "type": "PYTHON_UNITTEST_LOG", "scopeStatus": status,
        "total": total, "skipped": skipped, "excludedTests": excluded_tests,
        "fullSuiteCertified": False, "independentAuditPass": False,
    }


def create_local_evidence_receipt(*, source_commit_sha: str,
                                  command_argv: list[str],
                                  artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(source_commit_sha, str) or not _HEX40.fullmatch(source_commit_sha):
        raise ValueError("source pin must be a 40-hex Git commit")
    if (not isinstance(command_argv, list) or not 1 <= len(command_argv) <= 32
        or any(not isinstance(a, str) or not a or len(a) > 200 or any(ord(c)<32 for c in a)
               for a in command_argv)):
        raise ValueError("explicit bounded command argv required")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_ARTIFACTS:
        raise ValueError("1..32 evidence inputs required")
    seen = set()
    inputs = []
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"name", "kind", "bytes", "excludedTests"}:
            raise ValueError("invalid evidence record")
        name, kind, data, excluded = (item[k] for k in ("name", "kind", "bytes", "excludedTests"))
        if not isinstance(name, str) or not _NAME.fullmatch(name) or ".." in name.split("/"):
            raise ValueError("invalid evidence name")
        lower = name.lower()
        if lower in seen:
            raise ValueError("duplicate case-insensitive evidence name")
        seen.add(lower)
        if type(data) is not bytes or len(data) > MAX_ARTIFACT_BYTES or _REDACTION.search(data):
            raise ValueError("oversized or potentially credential-containing evidence")
        if kind == "NUNIT_XML":
            if excluded != 0:
                raise ValueError("NUnit exclusions must be represented by actual test-run skips")
            result = parse_nunit_xml(data)
        elif kind == "PYTHON_UNITTEST_LOG":
            result = parse_python_unittest_log(data, excluded_tests=excluded)
        else:
            raise ValueError("unknown evidence kind")
        inputs.append({"name": name, "kind": kind, "sha256": hashlib.sha256(data).hexdigest(),
                       "byteCount": len(data), "verification": result,
                       "storageRoute": "DRIVE_05_EVIDENCE_ONLY", "excludeFromPlayer": True})
    entries = sorted(inputs, key=lambda row: row["name"])
    receipt = {
        "schemaVersion": 1,
        "resultStatus": "REPRODUCIBLE_EVIDENCE_RECEIPT_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "sourceCommitSha": source_commit_sha,
        "commandArgv": command_argv[:],
        "files": entries,
        "allListedScopesPassed": all(x["verification"]["scopeStatus"] == "SCOPED_PASS" for x in entries),
        "independentAuditPerformed": False,
        "productionReleaseAuthorized": False,
    }
    encoded=json.dumps(receipt,sort_keys=True,ensure_ascii=False,separators=(",", ":")).encode("utf-8")
    receipt["receiptSha256"] = hashlib.sha256(encoded).hexdigest()
    return receipt

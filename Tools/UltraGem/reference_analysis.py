"""Read-only local UltraGem result inspector (NO gameplay or Engine parity).

LFX-M05-001 and LFX-M06-007/011 source preparation. Report only:
static features, structural near-duplicates, and explicit source/policy gates.
No publication, no writes, no simulated winning or synthetic difficulty grade.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import leveldraft
from candidate_diversity import screen_catalog
from reference_features import extract_reference_features

MAX_INSPECTION_BYTES = 2_000_000


def analyze_ranked_output(value: dict[str, Any], *, threshold: float = 0.95) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("resultStatus") != "REFERENCE_ONLY_UNVERIFIED" or value.get("engineStatus") != "BLOCKED_ENG_M24":
        raise ValueError("Only pinned reference-only Engine-blocked UltraGem results can be inspected")
    candidates = value.get("drafts")
    if not isinstance(candidates, list) or len(candidates) > 64:
        raise ValueError("drafts must be an array within the 64-entry budget")
    dataset = []
    features = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict) or not isinstance(item.get("draft"), dict):
            raise ValueError(f"drafts[{index}] is not a structured draft record")
        draft = item["draft"]
        leveldraft.validate(draft)
        digest = leveldraft.sha256(draft)
        if item.get("draftSha256") != digest:
            raise ValueError(f"drafts[{index}] declared SHA256 disagrees with canonical draft")
        compatibility = item.get("profileCompatibility")
        if not isinstance(compatibility, dict) or compatibility.get("engineStatus") != "BLOCKED_ENG_M24" or compatibility.get("draftMutationPerformed") is not False:
            raise ValueError(f"drafts[{index}] lacks honest profile/Engine boundary")
        candidate_id = f"draft.{index:04d}"
        dataset.append((candidate_id, draft))
        features.append({"candidateId": candidate_id, "sourceDraftSha256": digest,
                         "features": extract_reference_features(draft)})
    return {
        "resultStatus": "REFERENCE_ANALYSIS_ONLY",
        "engineStatus": "BLOCKED_ENG_M24",
        "releaseAuthorized": False,
        "sourceRepository": value.get("sourceRepository"),
        "sourceRevision": value.get("sourceRevision"),
        "seed": value.get("seed"),
        "candidateCount": len(dataset),
        "staticFeatures": features,
        "structuralDiversity": screen_catalog(dataset, threshold=threshold),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only reference-only feature and diversity report")
    parser.add_argument("--input", required=True, type=Path, help="existing UltraGem result JSON (read only)")
    parser.add_argument("--threshold", type=float, default=0.95)
    args = parser.parse_args(argv)
    try:
        p = args.input
        if not p.is_file() or p.stat().st_size > MAX_INSPECTION_BYTES:
            raise ValueError("input must be an existing JSON file no larger than 2 MB")
        # No producer output, input file, stage, backup or workspace is written.
        value = json.loads(p.read_text(encoding="utf-8"))
        result = analyze_ranked_output(value, threshold=args.threshold)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"invalid_reference_input: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

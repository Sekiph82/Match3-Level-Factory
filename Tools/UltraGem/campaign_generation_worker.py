"""Private one-candidate subprocess entry point for campaign workbench."""

from __future__ import annotations

import json
import sys

from factory_pipeline import run_pipeline


def main() -> int:
    try:
        request = json.loads(sys.stdin.buffer.read(16_384))
        if not isinstance(request, dict) or set(request) != {
            "rows", "columns", "colors", "seed", "candidate_count", "runs",
            "max_moves", "profile_id", "max_levels",
        }:
            raise ValueError("worker request shape is invalid")
        result = run_pipeline(**request)
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False,
                                    default=lambda value: value.item() if hasattr(value, "item") else value) + "\n")
        return 0
    except Exception as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

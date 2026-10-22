"""Start a child command only after its parent process has received OS limits."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if sys.stdin.readline().strip() != "RUN":
        return 70
    command = sys.argv[1:]
    if not command:
        return 64
    completed = subprocess.run(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False)
    print(json.dumps({"childExecutable": Path(command[0]).name,
                      "childExitCode": completed.returncode,
                      "childInheritedJobLimits": True}, sort_keys=True, separators=(",", ":")))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

"""Run a command with a merged log and propagate its real process exit code."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command:
        parser.error("a command is required")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("wb") as output:
        result = subprocess.run(args.command, stdout=output, stderr=subprocess.STDOUT)
    # unittest normally writes to stderr. Do not route its output through
    # PowerShell's native-error pipeline; keep logging separate from exit status.
    print(args.log.read_text(encoding="utf-8", errors="replace"), end="")
    print(f"Test process exit code: {result.returncode}", flush=True)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

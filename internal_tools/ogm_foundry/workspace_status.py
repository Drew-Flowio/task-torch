"""Print Foundry workspace status and next manual actions."""

from __future__ import annotations

import argparse
import json
import sys

from internal_tools.ogm_foundry.workspace_report import format_workspace_status, load_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show Foundry workspace status.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args(argv)

    try:
        payload = load_status()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_workspace_status(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

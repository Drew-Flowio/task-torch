"""Record human approval for a recommended candidate."""

from __future__ import annotations

import argparse
import json
import sys

from internal_tools.ogm_foundry.approve_workflow import approve_candidate
from internal_tools.ogm_foundry.runtime import load_services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Approve a recommended Foundry candidate for intake.")
    parser.add_argument("candidate_id", help="Candidate ID to approve")
    parser.add_argument("--actor", required=True, help="Human reviewer name or ID")
    parser.add_argument("--notes", required=True, help="Approval notes")
    args = parser.parse_args(argv)

    try:
        services = load_services()
        result = approve_candidate(
            services,
            args.candidate_id,
            actor=args.actor,
            notes=args.notes,
        )
    except (RuntimeError, PermissionError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    print("Human approval recorded. Vault intake was not performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

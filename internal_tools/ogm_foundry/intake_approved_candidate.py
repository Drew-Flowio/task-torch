"""Vault and bridge an approved candidate into repository evidence."""

from __future__ import annotations

import argparse
import json
import sys

from internal_tools.ogm_foundry.intake_workflow import intake_approved_candidate
from internal_tools.ogm_foundry.runtime import load_services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vault and bridge an approved Foundry candidate.")
    parser.add_argument("candidate_id", help="Approved candidate ID")
    parser.add_argument("--actor", default="foundry-cli", help="Actor performing intake")
    parser.add_argument(
        "--strict-license-review",
        action="store_true",
        help="Require complete license review evidence before intake",
    )
    args = parser.parse_args(argv)

    try:
        services = load_services()
        result = intake_approved_candidate(
            services,
            args.candidate_id,
            actor=args.actor,
            strict_license_review=args.strict_license_review,
        )
    except (RuntimeError, PermissionError, FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    print("Approved candidate vaulted, bridged to repository evidence, and CRS evaluation updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

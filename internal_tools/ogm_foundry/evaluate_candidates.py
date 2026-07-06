"""Evaluate submitted candidates with Curator-001."""

from __future__ import annotations

import argparse
import json
import sys

from internal_tools.ogm_foundry.curator_workflow import evaluate_candidates
from internal_tools.ogm_foundry.runtime import load_services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate submitted Foundry candidates with Curator-001.")
    parser.add_argument("--mission-id", dest="mission_id")
    parser.add_argument("--coverage-object-id", dest="coverage_object_id")
    parser.add_argument("--candidate-id", dest="candidate_id")
    args = parser.parse_args(argv)

    try:
        services = load_services()
        result = evaluate_candidates(
            services,
            mission_id=args.mission_id,
            coverage_object_id=args.coverage_object_id,
            candidate_id=args.candidate_id,
        )
    except (RuntimeError, ValueError, PermissionError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    print("Curator evaluation complete. No approvals or vault intake were performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

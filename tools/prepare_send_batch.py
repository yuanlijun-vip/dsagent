from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refund_recovery.sending import next_send_candidates, release_reservations, reserve_candidates
from tools.apply_send_logs import DEFAULT_WORKBOOK


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and optionally reserve a batch of refund recovery sends.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--shop")
    parser.add_argument("--reserve", action="store_true")
    parser.add_argument("--release-rows", nargs="*", type=int)
    args = parser.parse_args()

    if args.release_rows:
        release_reservations(args.workbook, args.release_rows)
        print(json.dumps({"released_rows": args.release_rows}, ensure_ascii=False, indent=2))
        return

    candidates = next_send_candidates(args.workbook, limit=max(1, args.limit), shop=args.shop)
    if args.reserve:
        reserve_candidates(args.workbook, candidates)

    print(
        json.dumps(
            {
                "workbook": str(args.workbook),
                "reserved": bool(args.reserve),
                "candidates": [candidate.to_dict() for candidate in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

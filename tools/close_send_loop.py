from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refund_recovery.closure import sync_closure_to_dingtalk, update_local_summary
from refund_recovery.dingtalk import DingTalkClient
from tools.apply_send_logs import DEFAULT_LOG, DEFAULT_WORKBOOK, apply_send_log


DEFAULT_NODE = "oP0MALyR8kmzea25UYyakR1kV3bzYmDO"
DEFAULT_DETAIL_SHEET_ID = "st-9db4499d-9689106"
DEFAULT_SUMMARY_SHEET_ID = "st-9db4499d-9407173"


def main() -> None:
    parser = argparse.ArgumentParser(description="Close the refund recovery send loop.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--node", default=DEFAULT_NODE)
    parser.add_argument("--detail-sheet-id", default=DEFAULT_DETAIL_SHEET_ID)
    parser.add_argument("--summary-sheet-id", default=DEFAULT_SUMMARY_SHEET_ID)
    parser.add_argument("--skip-dingtalk", action="store_true")
    args = parser.parse_args()

    applied = apply_send_log(args.workbook, args.log)
    update_local_summary(args.workbook)

    synced = None
    row_indexes = [int(row["row"]) for row in applied if row.get("row")]
    if not args.skip_dingtalk:
        synced = sync_closure_to_dingtalk(
            workbook_path=args.workbook,
            dingtalk=DingTalkClient(),
            node=args.node,
            detail_sheet_id=args.detail_sheet_id,
            summary_sheet_id=args.summary_sheet_id,
            detail_row_indexes=row_indexes,
        )

    print(
        json.dumps(
            {
                "workbook": str(args.workbook),
                "send_log": str(args.log),
                "applied": applied,
                "dingtalk_synced": None if synced is None else synced.__dict__,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

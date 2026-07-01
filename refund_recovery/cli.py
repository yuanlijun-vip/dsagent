from __future__ import annotations

import argparse
import json
import time
from datetime import datetime

from .config import load_config
from .dingtalk import DingTalkClient
from .workflow import RefundRecoveryWorkflow, previous_day_window


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="未发货仅退款客户挽回自动化 v1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="运行一次抓取结果处理")
    run.add_argument("--config", default="config.local.json", help="配置文件路径")
    run.add_argument("--dry-run", action="store_true", help="只输出结果，不写入钉钉")

    loop = subparsers.add_parser("loop", help="在配置的运行时段内循环执行")
    loop.add_argument("--config", default="config.local.json", help="配置文件路径")
    loop.add_argument("--sleep-seconds", type=int, default=60, help="每轮之间的等待秒数")
    loop.add_argument("--dry-run", action="store_true", help="只输出结果，不写入钉钉")

    window = subparsers.add_parser("window", help="显示当前应抓取的时间窗")
    window.add_argument("--now", default=None, help="固定当前时间，格式 YYYY-mm-dd HH:MM:SS")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "window":
        now = datetime.strptime(args.now, "%Y-%m-%d %H:%M:%S") if args.now else datetime.now()
        start, end = previous_day_window(now)
        print(json.dumps({"start": start.isoformat(sep=" "), "end": end.isoformat(sep=" ")}, ensure_ascii=False))
        return

    config = load_config(args.config)
    workflow = RefundRecoveryWorkflow(config, DingTalkClient(retry_count=config.runtime.retry_count))
    if args.command == "loop":
        while True:
            now = datetime.now()
            if _inside_runtime(now, config.runtime.start_time, config.runtime.end_time):
                result = workflow.run_once(dry_run=args.dry_run, now=now)
                print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2))
            time.sleep(max(1, args.sleep_seconds))
    result = workflow.run_once(dry_run=args.dry_run)
    print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2))


def _result_payload(result) -> dict:
    return {
        "enabled_shop_count": len(result.enabled_shops),
        "record_count": len(result.records),
        "skipped_existing_count": result.skipped_existing_count,
        "report_node": result.report_node,
        "report_sheet_id": result.report_sheet_id,
        "status_counts": _status_counts(result.records),
    }


def _inside_runtime(now: datetime, start_time: str, end_time: str) -> bool:
    start = datetime.strptime(start_time, "%H:%M").time()
    end = datetime.strptime(end_time, "%H:%M").time()
    current = now.time()
    return start <= current <= end


def _status_counts(records) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.status] = counts.get(record.status, 0) + 1
    return counts


if __name__ == "__main__":
    main()

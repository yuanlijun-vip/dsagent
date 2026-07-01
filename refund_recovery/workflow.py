from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from .config import AppConfig
from .dingtalk import DingTalkClient, enabled_shops, ensure_report_sheet
from .models import FollowUpRecord, RefundOrder, Shop
from .parser import ExportParseError, iter_export_files, parse_export_file
from .probes import CustomerProbeProvider, NoopCustomerProbeProvider
from .state import MonthlyReportState


@dataclass(frozen=True)
class RunResult:
    report_node: str
    report_sheet_id: str
    records: list[FollowUpRecord]
    enabled_shops: list[Shop]
    skipped_existing_count: int = 0


def previous_day_window(now: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine((now - timedelta(days=1)).date(), time.min)
    end = datetime.combine(now.date(), time.max).replace(microsecond=0)
    return start, end


def month_key(now: datetime) -> str:
    return now.strftime("%Y-%m")


def monthly_report_name(template: str, now: datetime) -> str:
    return template.replace("{yyyy}", now.strftime("%Y")).replace("{mm}", now.strftime("%m"))


class RefundRecoveryWorkflow:
    def __init__(
        self,
        config: AppConfig,
        dingtalk: DingTalkClient,
        probe_provider: CustomerProbeProvider | None = None,
    ) -> None:
        self.config = config
        self.dingtalk = dingtalk
        self.probe_provider = probe_provider or NoopCustomerProbeProvider()
        if self.config.runtime.send_messages:
            raise ValueError("send_messages must stay false in v1")

    def run_once(self, dry_run: bool = False, now: datetime | None = None) -> RunResult:
        now = now or datetime.now()
        shops = self._load_enabled_shops()
        report_node, report_sheet_id, existing_keys, existing_order_keys = self._prepare_report(dry_run, now)
        records: list[FollowUpRecord] = []
        skipped_existing_count = 0
        seen_keys = set(existing_keys)
        for shop in shops:
            for order in self._load_shop_orders(shop, now):
                order_key = (order.shop_name, order.order_id, order.buyer_id)
                if order.order_id and order_key in existing_order_keys:
                    skipped_existing_count += 1
                    continue
                record = self._build_record(order, seen_keys, now)
                records.append(record)
                if record.buyer_id:
                    seen_keys.add((record.shop_name, record.buyer_id))
        if not dry_run:
            self.dingtalk.append_rows(report_node, report_sheet_id, [record.to_row() for record in records])
        return RunResult(
            report_node=report_node,
            report_sheet_id=report_sheet_id,
            records=records,
            enabled_shops=shops,
            skipped_existing_count=skipped_existing_count,
        )

    def _load_enabled_shops(self) -> list[Shop]:
        rows = self.dingtalk.read_range(self.config.shop_list_node, self.config.shop_list_sheet)
        return enabled_shops(rows, self.config.shop_name_column, self.config.shop_enabled_column)

    def _prepare_report(
        self, dry_run: bool, now: datetime
    ) -> tuple[str, str, set[tuple[str, str]], set[tuple[str, str, str]]]:
        node = self.config.monthly_report.existing_node
        sheet_id = self.config.monthly_report.sheet_name
        month = month_key(now)
        if not node:
            state = MonthlyReportState(self.config.state_file)
            node = state.get(month)
        if not node:
            if dry_run:
                node = "DRY-RUN-MONTHLY-REPORT"
            else:
                node = self.dingtalk.create_spreadsheet(
                    monthly_report_name(self.config.monthly_report.name_template, now),
                    self.config.monthly_report.folder,
                )
                MonthlyReportState(self.config.state_file).set(month, node)
        if not dry_run:
            sheet_id = ensure_report_sheet(self.dingtalk, node, self.config.monthly_report.sheet_name)
            existing_rows = self.dingtalk.read_range(node, sheet_id)
        else:
            existing_rows = []
        return node, sheet_id, _existing_followup_keys(existing_rows), _existing_order_keys(existing_rows)

    def _load_shop_orders(self, shop: Shop, now: datetime) -> list[RefundOrder]:
        orders: list[RefundOrder] = []
        for path in _matching_export_files(self.config.export_dir, shop.name):
            try:
                orders.extend(parse_export_file(path, shop.name, self.config.columns))
            except Exception as exc:
                orders.append(
                    RefundOrder(
                        shop_name=shop.name,
                        order_id="",
                        buyer_id="",
                        refund_time="",
                        order_status="",
                        source_file=path.name,
                        parse_error=str(exc),
                    )
                )
        return orders

    def _build_record(
        self,
        order: RefundOrder,
        seen_keys: set[tuple[str, str]],
        now: datetime,
    ) -> FollowUpRecord:
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        duplicate = bool(order.buyer_id and (order.shop_name, order.buyer_id) in seen_keys)
        probe = self.probe_provider.probe(order) if order.buyer_id else None
        if order.parse_error:
            status = "失败-异常原因"
            reason = f"字段解析失败：{order.parse_error}"
            today_chatted = False
            has_unfinished = False
        elif not order.buyer_id:
            status = "失败-异常原因"
            reason = "缺少旺旺ID"
            today_chatted = False
            has_unfinished = False
        elif probe and probe.error:
            status = "失败-异常原因"
            reason = probe.error
            today_chatted = probe.today_chatted
            has_unfinished = probe.has_unfinished_order
        elif duplicate:
            status = "跳过-当月重复"
            reason = "同一月份同一店铺旺旺ID已存在"
            today_chatted = bool(probe and probe.today_chatted)
            has_unfinished = bool(probe and probe.has_unfinished_order)
        elif probe and probe.today_chatted:
            status = "跳过-今日已对话"
            reason = "客户今日已有对话"
            today_chatted = True
            has_unfinished = probe.has_unfinished_order
        elif probe and probe.has_unfinished_order:
            status = "跳过-存在未完结订单"
            reason = "客户存在未完结订单"
            today_chatted = probe.today_chatted
            has_unfinished = True
        else:
            status = "待发送"
            reason = ""
            today_chatted = False
            has_unfinished = False
        return FollowUpRecord(
            month=month_key(now),
            shop_name=order.shop_name,
            order_id=order.order_id,
            buyer_id=order.buyer_id,
            refund_time=order.refund_time,
            order_status=order.order_status,
            has_unfinished_order=has_unfinished,
            today_chatted=today_chatted,
            is_monthly_duplicate=duplicate,
            status=status,
            skip_reason=reason,
            source_file=order.source_file,
            created_at=created_at,
            updated_at=created_at,
        )


def _matching_export_files(export_dir: Path, shop_name: str) -> list[Path]:
    return [path for path in iter_export_files(export_dir) if shop_name in path.stem]


def _existing_followup_keys(rows: list[list[str]]) -> set[tuple[str, str]]:
    if not rows:
        return set()
    headers = [str(cell).strip() for cell in rows[0]]
    try:
        shop_index = headers.index("店铺名")
        buyer_index = headers.index("旺旺ID")
    except ValueError:
        return set()
    keys: set[tuple[str, str]] = set()
    for row in rows[1:]:
        shop = str(row[shop_index]).strip() if shop_index < len(row) else ""
        buyer = str(row[buyer_index]).strip() if buyer_index < len(row) else ""
        if shop and buyer:
            keys.add((shop, buyer))
    return keys


def _existing_order_keys(rows: list[list[str]]) -> set[tuple[str, str, str]]:
    if not rows:
        return set()
    headers = [str(cell).strip() for cell in rows[0]]
    try:
        shop_index = headers.index("店铺名")
        order_index = headers.index("订单号")
        buyer_index = headers.index("旺旺ID")
    except ValueError:
        return set()
    keys: set[tuple[str, str, str]] = set()
    for row in rows[1:]:
        shop = str(row[shop_index]).strip() if shop_index < len(row) else ""
        order = str(row[order_index]).strip() if order_index < len(row) else ""
        buyer = str(row[buyer_index]).strip() if buyer_index < len(row) else ""
        if shop and order:
            keys.add((shop, order, buyer))
    return keys

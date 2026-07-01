from __future__ import annotations

from dataclasses import dataclass


REPORT_HEADERS = [
    "月份",
    "店铺名",
    "订单号",
    "旺旺ID",
    "退款申请时间",
    "订单状态",
    "是否未完结订单",
    "今日是否已对话",
    "是否当月重复",
    "处理状态",
    "跳过原因",
    "导出文件名",
    "创建时间",
    "更新时间",
]


@dataclass(frozen=True)
class Shop:
    name: str
    raw: dict[str, str]


@dataclass(frozen=True)
class RefundOrder:
    shop_name: str
    order_id: str
    buyer_id: str
    refund_time: str
    order_status: str
    source_file: str
    today_chatted: bool = False
    has_unfinished_order: bool = False
    parse_error: str = ""


@dataclass(frozen=True)
class CustomerProbe:
    today_chatted: bool = False
    has_unfinished_order: bool = False
    error: str = ""


@dataclass(frozen=True)
class FollowUpRecord:
    month: str
    shop_name: str
    order_id: str
    buyer_id: str
    refund_time: str
    order_status: str
    has_unfinished_order: bool
    today_chatted: bool
    is_monthly_duplicate: bool
    status: str
    skip_reason: str
    source_file: str
    created_at: str
    updated_at: str

    def to_row(self) -> list[str]:
        return [
            self.month,
            self.shop_name,
            self.order_id,
            self.buyer_id,
            self.refund_time,
            self.order_status,
            "是" if self.has_unfinished_order else "否",
            "是" if self.today_chatted else "否",
            "是" if self.is_monthly_duplicate else "否",
            self.status,
            self.skip_reason,
            self.source_file,
            self.created_at,
            self.updated_at,
        ]

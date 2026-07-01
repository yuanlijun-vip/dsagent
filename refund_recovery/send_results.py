from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


SEND_HEADERS = ["发送状态", "发送时间", "发送内容版本", "发送详情"]


@dataclass(frozen=True)
class SendResult:
    shop: str
    order_id: str
    buyer_id: str
    result: str
    sent_parts: tuple[str, ...]
    not_sent_parts: tuple[str, ...]
    note: str
    sent_at: str
    template_version: str

    @property
    def send_status(self) -> str:
        if self.result == "sent":
            return "已发送"
        if self.result == "partial_sent":
            return "部分发送"
        if self.result in {"blocked_by_warning", "warning_blocked"}:
            return "风控拦截"
        if self.result in {"target_mismatch", "wrong_target"}:
            return "目标不一致"
        return "发送异常"

    @property
    def process_status(self) -> str:
        return "已发送" if self.result == "sent" else "发送异常"

    @property
    def detail(self) -> str:
        parts: list[str] = []
        if self.sent_parts:
            parts.append(f"已发送: {', '.join(self.sent_parts)}")
        if self.not_sent_parts:
            parts.append(f"未发送: {', '.join(self.not_sent_parts)}")
        if self.note:
            parts.append(self.note)
        return "；".join(parts)


def template_version_from_path(path: str) -> str:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0] if name else ""


def load_send_results(log_data: dict[str, Any]) -> list[SendResult]:
    sent_at = str(log_data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    template_version = template_version_from_path(str(log_data.get("message_template") or ""))
    results: list[SendResult] = []
    for row in log_data.get("results") or []:
        results.append(
            SendResult(
                shop=str(row.get("shop") or "").strip(),
                order_id=str(row.get("order_id") or "").strip(),
                buyer_id=str(row.get("buyer_id") or "").strip(),
                result=str(row.get("result") or "").strip(),
                sent_parts=tuple(str(part) for part in row.get("sent_parts") or ()),
                not_sent_parts=tuple(str(part) for part in row.get("not_sent_parts") or ()),
                note=str(row.get("note") or "").strip(),
                sent_at=str(row.get("sent_at") or sent_at),
                template_version=template_version,
            )
        )
    return results

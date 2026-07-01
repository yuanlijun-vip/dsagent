from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    start_time: str
    end_time: str
    retry_count: int
    send_messages: bool


@dataclass(frozen=True)
class MonthlyReportConfig:
    name_template: str
    folder: str | None
    existing_node: str | None
    sheet_name: str


@dataclass(frozen=True)
class MessageTemplateConfig:
    path: Path | None


@dataclass(frozen=True)
class AppConfig:
    shop_list_node: str
    shop_list_sheet: str | None
    shop_enabled_column: str
    shop_name_column: str
    export_dir: Path
    runtime: RuntimeConfig
    monthly_report: MonthlyReportConfig
    message_template: MessageTemplateConfig
    columns: dict[str, list[str]]
    state_file: Path


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    runtime = data.get("runtime", {})
    monthly = data.get("monthly_report", {})
    message_template = data.get("message_template", {})
    template_path = message_template.get("path")
    return AppConfig(
        shop_list_node=data["shop_list_node"],
        shop_list_sheet=data.get("shop_list_sheet"),
        shop_enabled_column=data.get("shop_enabled_column", "是否"),
        shop_name_column=data.get("shop_name_column", "店铺名"),
        export_dir=(config_path.parent / data.get("export_dir", "exports")).resolve(),
        runtime=RuntimeConfig(
            start_time=runtime.get("start_time", "08:00"),
            end_time=runtime.get("end_time", "23:30"),
            retry_count=int(runtime.get("retry_count", 3)),
            send_messages=bool(runtime.get("send_messages", False)),
        ),
        monthly_report=MonthlyReportConfig(
            name_template=monthly.get("name_template", "未发货仅退款客户挽回跟进-{yyyy}-{mm}"),
            folder=monthly.get("folder"),
            existing_node=monthly.get("existing_node"),
            sheet_name=monthly.get("sheet_name", "跟进明细"),
        ),
        message_template=MessageTemplateConfig(
            path=(config_path.parent / template_path).resolve() if template_path else None,
        ),
        columns=data.get("columns", {}),
        state_file=(config_path.parent / data.get("state_file", ".runtime/monthly_reports.json")).resolve(),
    )

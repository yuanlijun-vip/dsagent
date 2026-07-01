from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import REPORT_HEADERS, Shop


DEFAULT_NODE = Path(
    r"C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)
DEFAULT_DWS = Path(
    r"C:\Users\Admin\Documents\Codex\2026-06-26\github-linear\work\pnpm-home\global\v11\5ea4-19f030f751d\node_modules\dingtalk-workspace-cli\bin\dws.js"
)


class DingTalkError(RuntimeError):
    pass


class DingTalkClient:
    def __init__(
        self,
        node_path: Path = DEFAULT_NODE,
        dws_path: Path = DEFAULT_DWS,
        retry_count: int = 3,
    ) -> None:
        self.node_path = node_path
        self.dws_path = dws_path
        self.retry_count = retry_count

    def _run(self, args: list[str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(max(1, self.retry_count)):
            try:
                return self._run_once(args)
            except DingTalkError as exc:
                last_error = exc
                if attempt < self.retry_count - 1:
                    time.sleep(1)
        raise last_error or DingTalkError("Unknown DingTalk CLI error")

    def _run_once(self, args: list[str]) -> dict[str, Any]:
        if not self.node_path.exists():
            raise DingTalkError(f"Node executable not found: {self.node_path}")
        if not self.dws_path.exists():
            raise DingTalkError(f"dws CLI not found: {self.dws_path}")
        completed = subprocess.run(
            [str(self.node_path), str(self.dws_path), *args, "-f", "json"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as exc:
            raise DingTalkError(output) from exc
        if completed.returncode != 0 or payload.get("success") is False or payload.get("error"):
            raise DingTalkError(json.dumps(payload, ensure_ascii=False))
        return payload

    def list_sheets(self, node: str) -> list[dict[str, Any]]:
        payload = self._run(["sheet", "list", "--node", node])
        return list(payload.get("sheets", []))

    def read_range(self, node: str, sheet_id: str | None = None, range_a1: str | None = None) -> list[list[str]]:
        args = ["sheet", "range", "read", "--node", node]
        if sheet_id:
            args += ["--sheet-id", sheet_id]
        if range_a1:
            args += ["--range", range_a1]
        payload = self._run(args)
        return payload.get("values") or payload.get("displayValues") or []

    def append_rows(self, node: str, sheet_id: str, rows: list[list[str]]) -> None:
        if not rows:
            return
        self._run(
            [
                "sheet",
                "append",
                "--node",
                node,
                "--sheet-id",
                sheet_id,
                "--values",
                json.dumps(rows, ensure_ascii=True),
            ]
        )

    def update_range(self, node: str, sheet_id: str, range_a1: str, values: list[list[Any]]) -> None:
        self._run(
            [
                "sheet",
                "range",
                "update",
                "--node",
                node,
                "--sheet-id",
                sheet_id,
                "--range",
                range_a1,
                "--values",
                json.dumps(values, ensure_ascii=True),
            ]
        )

    def create_spreadsheet(self, name: str, folder: str | None = None) -> str:
        args = ["sheet", "create", "--name", name]
        if folder:
            args += ["--folder", folder]
        payload = self._run(args)
        for key in ("nodeId", "docUrl", "url"):
            if payload.get(key):
                return str(payload[key])
        result = payload.get("result") or {}
        for key in ("nodeId", "docUrl", "url"):
            if result.get(key):
                return str(result[key])
        raise DingTalkError(f"Cannot locate created spreadsheet node in: {payload}")

    def new_sheet(self, node: str, name: str) -> str:
        payload = self._run(["sheet", "new", "--node", node, "--name", name])
        sheet = payload.get("sheet") or payload.get("result") or payload
        return str(sheet.get("sheetId") or sheet.get("id") or name)


def rows_to_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [str(cell).strip() for cell in rows[0]]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        record = {
            header: str(row[index]).strip() if index < len(row) and row[index] is not None else ""
            for index, header in enumerate(headers)
            if header
        }
        if any(record.values()):
            records.append(record)
    return records


def enabled_shops(rows: list[list[str]], name_column: str, enabled_column: str) -> list[Shop]:
    shops: list[Shop] = []
    for record in rows_to_dicts(rows):
        if record.get(enabled_column, "").strip() == "是":
            name = record.get(name_column, "").strip()
            if name:
                shops.append(Shop(name=name, raw=record))
    return shops


def ensure_report_sheet(client: DingTalkClient, node: str, sheet_name: str) -> str:
    sheets = client.list_sheets(node)
    for sheet in sheets:
        if sheet.get("name") == sheet_name:
            sheet_id = str(sheet.get("sheetId") or sheet_name)
            if not client.read_range(node, sheet_id, "A1:N1"):
                client.append_rows(node, sheet_id, [REPORT_HEADERS])
            return sheet_id
    sheet_id = client.new_sheet(node, sheet_name)
    client.append_rows(node, sheet_id, [REPORT_HEADERS])
    return sheet_id

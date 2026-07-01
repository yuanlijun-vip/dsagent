from __future__ import annotations

import json
from pathlib import Path


class MonthlyReportState:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    def get(self, month: str) -> str | None:
        value = self.data.get(month)
        return str(value) if value else None

    def set(self, month: str, node: str) -> None:
        self.data[month] = node
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

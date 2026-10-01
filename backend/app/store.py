"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        # guard_* 是第三方施工监护台账的内部表（项目/交底/旁站记录），
        # 不单独作为业务模块展示；监护口径统一在卡片「在建监护数」里呈现。
        guard_names = {"guard_project", "guard_briefing", "guard_watch"}
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            if name in guard_names:
                continue
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        # 在建监护数：只统计未完工项目，与待监护视图（/api/guard?scope=pending）同口径。
        active_guard = sum(
            1 for row in self.rows("guard_project") if row.get("status") != "已完工"
        )
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
            {"label": "在建监护数", "value": active_guard},
        ]
        return {"cards": cards, "modules": modules}


store = Store()

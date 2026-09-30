"""第三方施工监护台账业务规则。

台账由三张表聚合而成：
- guard_project：外部单位施工项目（在建 / 已完工）；
- guard_briefing：施工交底，同一项目重复报送只保留最新一版；
- guard_record：每次旁站监护明细，发现违章需闭环后项目才允许完工。

视图上的交底时间、监护人、监护记录条数、待监护口径都在这里统一计算，
保证台账列表、项目明细、运营概览三处看到的数字始终对得上。
"""
from __future__ import annotations

from typing import Any

from app.store import store

PROJECT_TABLE = "guard_project"
BRIEFING_TABLE = "guard_briefing"
RECORD_TABLE = "guard_record"
# 三张表由本服务自行聚合，不参与通用模块概览遍历。
GUARD_TABLES = {PROJECT_TABLE, BRIEFING_TABLE, RECORD_TABLE}

STATUS_IN_PROGRESS = "在建"
STATUS_COMPLETED = "已完工"
RESULT_NORMAL = "正常"
RESULT_VIOLATION = "发现违章"

PROJECT_REQUIRED_FIELDS = ["项目名称", "外部单位", "涉及管段"]
BRIEFING_REQUIRED_FIELDS = ["交底时间", "交底人员", "监护人"]
RECORD_REQUIRED_FIELDS = ["监护时间", "监护人", "监护内容", "监护结论"]
RECORD_RESULTS = [RESULT_NORMAL, RESULT_VIOLATION]


def _next_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


class GuardService:
    # ---------- 内部聚合口径 ----------
    def _briefings(self, project_id: int) -> list[dict[str, Any]]:
        return [row for row in store.rows(BRIEFING_TABLE) if int(row.get("项目id", 0)) == project_id]

    def latest_briefing(self, project_id: int) -> dict[str, Any] | None:
        rows = self._briefings(project_id)
        if not rows:
            return None
        # 同一项目只认最新一版：以自增 id 最大者为准（重复报送覆盖前，先取出老版本删除）。
        return max(rows, key=lambda row: int(row.get("id", 0)))

    def _records(self, project_id: int) -> list[dict[str, Any]]:
        rows = [row for row in store.rows(RECORD_TABLE) if int(row.get("项目id", 0)) == project_id]
        return sorted(rows, key=lambda row: str(row.get("监护时间", "")), reverse=True)

    def _open_violation_count(self, project_id: int) -> int:
        return sum(
            1
            for row in self._records(project_id)
            if row.get("监护结论") == RESULT_VIOLATION and not row.get("是否闭环")
        )

    def _to_view(self, project: dict[str, Any]) -> dict[str, Any]:
        """把项目行组装成台账视图行：交底与监护信息全部实时聚合。"""
        project_id = int(project.get("id", 0))
        briefing = self.latest_briefing(project_id)
        records = self._records(project_id)
        open_violations = self._open_violation_count(project_id)
        return {
            **project,
            "交底时间": briefing.get("交底时间") if briefing else None,
            "交底人员": briefing.get("交底人员") if briefing else None,
            "监护人": briefing.get("监护人") if briefing else None,
            "是否已交底": briefing is not None,
            "监护记录条数": len(records),
            "未闭环违章数": open_violations,
        }

    # ---------- 台账视图 ----------
    def list_projects(
        self,
        *,
        keyword: str | None = None,
        scope: str = "pending",
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """列出施工监护台账。

        scope=pending 即「待监护视图」：只看在建项目，完工后不再进入；
        scope=all 时可按项目状态继续筛选。
        """
        rows = [self._to_view(row) for row in store.rows(PROJECT_TABLE)]
        if scope == "pending":
            rows = [row for row in rows if row.get("项目状态") == STATUS_IN_PROGRESS]
        elif status:
            rows = [row for row in rows if row.get("项目状态") == status]
        if keyword:
            keyword = keyword.strip()
            rows = [
                row
                for row in rows
                if keyword in str(row.get("项目名称", ""))
                or keyword in str(row.get("项目编号", ""))
                or keyword in str(row.get("外部单位", ""))
            ]
        # 未交底的项目排到最前面单独高亮，同组内按登记时间倒序（稳定排序两遍）。
        rows.sort(key=lambda row: str(row.get("登记日期", "")), reverse=True)
        rows.sort(key=lambda row: row["是否已交底"])
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_project_detail(self, project_id: int) -> dict[str, Any] | None:
        project = store.find(PROJECT_TABLE, project_id)
        if project is None:
            return None
        view = self._to_view(project)
        view["交底记录"] = self.latest_briefing(project_id)
        view["监护记录"] = self._records(project_id)
        return view

    # ---------- 写操作 ----------
    def create_project(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in PROJECT_REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(PROJECT_TABLE)
        project = {"id": _next_id(rows)}
        project["项目编号"] = f"GUARD-{project['id']:04d}"
        project.update({field: str(values.get(field)).strip() for field in PROJECT_REQUIRED_FIELDS})
        project["项目状态"] = STATUS_IN_PROGRESS
        project["登记日期"] = str(values.get("登记日期") or "").strip() or _today()
        project["完工日期"] = None
        rows.append(project)
        return project, []

    def submit_briefing(
        self, project_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """报送（或重复报送）施工交底：同一项目只留最新一版。"""
        project = store.find(PROJECT_TABLE, project_id)
        if project is None:
            return None, f"施工项目 {project_id} 不存在或已归档"
        missing = [field for field in BRIEFING_REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"

        rows = store.rows(BRIEFING_TABLE)
        old = self.latest_briefing(project_id)
        briefing = {"id": _next_id(rows), "项目id": project_id}
        for field in ("交底时间", "交底地点", "交底人员", "监护人", "交底内容"):
            briefing[field] = str(values.get(field) or "").strip()
        rows.append(briefing)
        if old is not None:
            # 重复报送只留最新一版：老版本从台账中移除。
            rows[:] = [row for row in rows if int(row.get("id", 0)) != int(old["id"])]
        return briefing, "交底已报送，重复报送已按最新版本留存" if old is not None else "施工交底已报送"

    def add_record(
        self, project_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """补录一次旁站监护明细；视图上的监护记录条数由聚合口径同步刷新。"""
        project = store.find(PROJECT_TABLE, project_id)
        if project is None:
            return None, f"施工项目 {project_id} 不存在或已归档"
        missing = [field for field in RECORD_REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, f"缺少必填字段：{'、'.join(missing)}"
        result = str(values.get("监护结论") or "").strip()
        if result not in RECORD_RESULTS:
            return None, f"监护结论只支持：{'、'.join(RECORD_RESULTS)}"

        rows = store.rows(RECORD_TABLE)
        record = {"id": _next_id(rows), "项目id": project_id}
        for field in ("监护时间", "监护地点", "监护人", "监护内容", "监护结论"):
            record[field] = str(values.get(field) or "").strip()
        record["是否闭环"] = result == RESULT_NORMAL
        rows.append(record)
        return record, "旁站监护记录已补录，台账条数已同步更新"

    def close_record(self, record_id: int) -> tuple[dict[str, Any] | None, str]:
        record = store.find(RECORD_TABLE, record_id)
        if record is None:
            return None, f"监护记录 {record_id} 不存在"
        if record.get("监护结论") != RESULT_VIOLATION:
            return None, "只有发现违章的监护记录需要闭环"
        if record.get("是否闭环"):
            return record, "该违章监护记录已闭环"
        record["是否闭环"] = True
        return record, "违章已闭环，项目可继续办理完工"

    def complete_project(self, project_id: int) -> tuple[dict[str, Any] | None, str]:
        """标注完工：存在未闭环的违章监护记录时拦下；完工后退出待监护视图。"""
        project = store.find(PROJECT_TABLE, project_id)
        if project is None:
            return None, f"施工项目 {project_id} 不存在或已归档"
        if project.get("项目状态") == STATUS_COMPLETED:
            return project, "该项目已标注完工"
        if self.latest_briefing(project_id) is None:
            return None, "项目尚未施工交底，不能标注完工"
        open_violations = self._open_violation_count(project_id)
        if open_violations:
            return None, f"还有 {open_violations} 条违章监护记录未闭环，不能标注完工"
        project["项目状态"] = STATUS_COMPLETED
        project["完工日期"] = _today()
        return project, "项目已标注完工，不再进入待监护视图"

    # ---------- 运营概览 ----------
    def overview_summary(self) -> dict[str, int]:
        """运营概览口径：在建监护数与待监护视图（scope=pending）条数严格一致。"""
        pending, _ = self.list_projects(scope="pending", page=1, size=100000)
        return {
            "在建监护数": len(pending),
            "未交底项目数": sum(1 for row in pending if not row["是否已交底"]),
            "未闭环违章数": sum(int(row["未闭环违章数"]) for row in pending),
        }

    def overview_module(self) -> dict[str, object]:
        """供 /api/overview 的模块表使用：created/pending/abnormal 口径与视图一致。"""
        pending, _ = self.list_projects(scope="pending", page=1, size=100000)
        return {
            "name": "第三方施工监护",
            "created": len(store.rows(PROJECT_TABLE)),
            "pending": len(pending),
            "abnormal": sum(1 for row in pending if int(row["未闭环违章数"]) > 0),
        }


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


guard_service = GuardService()

"""第三方施工监护台账业务规则。

台账由三张表聚合而成：
- guard_project：外部单位施工项目（在建/已完工）；
- guard_briefing：施工交底，同一项目重复报送只保留最新一版；
- guard_watch：每次旁站监护记录，发现违章的记录可闭环。

列表视图里的交底时间、监护人、监护记录条数都在本模块汇总，
运营概览的「在建监护数」直接复用同一口径，避免两处数字对不上。
"""
from __future__ import annotations

from typing import Any

from app.store import store

PROJECT_MODULE = "guard_project"
BRIEFING_MODULE = "guard_briefing"
WATCH_MODULE = "guard_watch"

STATUS_ACTIVE = "在建"
STATUS_DONE = "已完工"
PROJECT_STATUSES = [STATUS_ACTIVE, STATUS_DONE]

PROJECT_REQUIRED = ["项目编号", "项目名称", "外部单位", "涉及管段"]
BRIEFING_REQUIRED = ["交底时间", "交底人", "交底内容"]
WATCH_REQUIRED = ["监护日期", "监护时段", "监护人", "监护情况"]


def _next_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


def latest_briefing(project_id: int) -> dict[str, Any] | None:
    """取项目最新一版交底：重复报送交底时旧版只留作内部痕迹，视图只呈现最新版。"""
    briefings = [
        row for row in store.rows(BRIEFING_MODULE)
        if int(row.get("project_id", 0)) == project_id
    ]
    if not briefings:
        return None
    return max(briefings, key=lambda row: (str(row.get("交底时间", "")), int(row.get("id", 0))))


def watch_rows(project_id: int) -> list[dict[str, Any]]:
    """项目的全部旁站监护记录，按日期倒序，补录的新记录自然排到最前。"""
    rows = [
        row for row in store.rows(WATCH_MODULE)
        if int(row.get("project_id", 0)) == project_id
    ]
    return sorted(rows, key=lambda row: (str(row.get("监护日期", "")), int(row.get("id", 0))), reverse=True)


def decorate_project(project: dict[str, Any]) -> dict[str, Any]:
    """把交底与旁站监护信息汇总到项目行上，形成台账视图需要的字段。"""
    project_id = int(project.get("id", 0))
    briefing = latest_briefing(project_id)
    records = watch_rows(project_id)
    open_violations = [
        row for row in records
        if row.get("监护情况") == "发现违章" and row.get("闭环状态") != "已闭环"
    ]
    # 监护人按到场先后（记录登记顺序）去重，与记录列表的日期倒序区分开。
    all_records = sorted(store.rows(WATCH_MODULE), key=lambda row: int(row.get("id", 0)))
    guardians = list(dict.fromkeys(
        str(row.get("监护人", ""))
        for row in all_records
        if int(row.get("project_id", 0)) == project_id and row.get("监护人")
    ))
    view = dict(project)
    view["交底时间"] = briefing.get("交底时间") if briefing else None
    view["交底人"] = briefing.get("交底人") if briefing else None
    view["已交底"] = briefing is not None
    view["监护人"] = "、".join(guardians)
    view["监护记录条数"] = len(records)
    view["未闭环违章数"] = len(open_violations)
    return view


class GuardService:
    def list_projects(
        self,
        *,
        scope: str = "pending",
        keyword: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """台账列表：默认只看待监护（在建）项目，完工后可在全部台账里查到。"""
        rows = [decorate_project(row) for row in store.rows(PROJECT_MODULE)]
        if scope != "all":
            rows = [row for row in rows if row.get("status") != STATUS_DONE]
        if keyword:
            key = keyword.strip()
            rows = [
                row for row in rows
                if key in str(row.get("项目编号", ""))
                or key in str(row.get("项目名称", ""))
                or key in str(row.get("外部单位", ""))
            ]
        rows.sort(key=lambda row: int(row.get("id", 0)))
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def active_project_count(self) -> int:
        """在建监护数：与待监护视图同源，概览卡片直接调用这里。"""
        return sum(1 for row in store.rows(PROJECT_MODULE) if row.get("status") != STATUS_DONE)

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        """项目明细：汇总最新交底与每次旁站监护记录。"""
        project = store.find(PROJECT_MODULE, project_id)
        if project is None:
            return None
        view = decorate_project(project)
        view["交底记录"] = latest_briefing(project_id)
        view["监护记录"] = watch_rows(project_id)
        return view

    def submit_briefing(self, project_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]:
        """报送（或重复报送）施工交底：同一项目只留最新一版，旧版直接覆盖。"""
        project = store.find(PROJECT_MODULE, project_id)
        if project is None:
            return None, [], f"施工项目 {project_id} 不存在"
        missing = [field for field in BRIEFING_REQUIRED if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing, ""
        rows = store.rows(BRIEFING_MODULE)
        existing = latest_briefing(project_id)
        if existing is not None:
            briefing = existing
            briefing.update({field: values.get(field) for field in BRIEFING_REQUIRED})
            message = "交底已按最新版本更新，旧版不再展示"
        else:
            briefing = {"id": _next_id(rows)}
            briefing["project_id"] = project_id
            briefing.update({field: values.get(field) for field in BRIEFING_REQUIRED})
            rows.append(briefing)
            message = "施工交底已记录"
        return briefing, [], message

    def add_watch(self, project_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]:
        """补录一条旁站监护记录，列表视图上的监护记录条数随之自动加一。"""
        project = store.find(PROJECT_MODULE, project_id)
        if project is None:
            return None, [], f"施工项目 {project_id} 不存在"
        missing = [field for field in WATCH_REQUIRED if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing, ""
        situation = str(values.get("监护情况") or "").strip()
        if situation not in ("正常", "发现违章"):
            return None, [], "监护情况只支持「正常」或「发现违章」"
        rows = store.rows(WATCH_MODULE)
        record = {"id": _next_id(rows), "project_id": project_id}
        record.update({field: values.get(field) for field in WATCH_REQUIRED})
        record["问题描述"] = values.get("问题描述") or ""
        record["闭环状态"] = "已闭环" if situation == "正常" else "未闭环"
        rows.append(record)
        return record, [], "旁站监护记录已补录"

    def close_watch(self, project_id: int, watch_id: int) -> tuple[dict[str, Any] | None, str]:
        """闭环一条违章监护记录；闭环后项目才允许标注完工。"""
        record = None
        for row in store.rows(WATCH_MODULE):
            if int(row.get("id", 0)) == watch_id and int(row.get("project_id", 0)) == project_id:
                record = row
                break
        if record is None:
            return None, f"监护记录 {watch_id} 不属于该项目或不存在"
        if record.get("监护情况") != "发现违章":
            return None, "该记录为正常监护，无需闭环"
        if record.get("闭环状态") == "已闭环":
            return None, "该违章记录已闭环，请勿重复操作"
        record["闭环状态"] = "已闭环"
        return record, "违章监护记录已闭环"

    def finish_project(self, project_id: int) -> tuple[dict[str, Any] | None, str]:
        """标注完工：还有未闭环的违章监护记录时拦下；完工后项目退出待监护视图。"""
        project = store.find(PROJECT_MODULE, project_id)
        if project is None:
            return None, f"施工项目 {project_id} 不存在"
        if project.get("status") == STATUS_DONE:
            return None, "项目已标注完工，无需重复操作"
        records = watch_rows(project_id)
        open_violations = [
            row for row in records
            if row.get("监护情况") == "发现违章" and row.get("闭环状态") != "已闭环"
        ]
        if open_violations:
            ids = "、".join(str(row.get("id")) for row in open_violations)
            return None, f"还有 {len(open_violations)} 条违章监护记录（编号 {ids}）未闭环，不能标注完工"
        project["status"] = STATUS_DONE
        return project, "项目已标注完工，退出待监护视图"

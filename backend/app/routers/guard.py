"""第三方施工监护台账接口：项目台账视图、项目明细、交底报送、旁站记录补录与闭环、完工。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.guard import GuardService

router = APIRouter(prefix="/api/guard", tags=["第三方施工监护"])

service = GuardService()

COLUMNS = ["项目编号", "项目名称", "外部单位", "涉及管段", "交底时间", "监护人", "监护记录条数", "未闭环违章数"]


@router.get("", response_model=PageResult[dict])
def list_projects(
    scope: str = Query(default="pending", description="pending=待监护（在建）视图，all=含已完工的全部台账"),
    keyword: str | None = Query(default=None, description="按项目编号、名称或外部单位检索"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """列出施工监护台账；未交底的项目在返回行上以 已交底=false 标记，由前端高亮。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_projects(scope=scope, keyword=keyword, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{project_id}", response_model=dict)
def get_project(project_id: int) -> dict:
    """项目明细：最新一版交底与每次旁站监护记录都在这里呈现。"""
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"施工项目 {project_id} 不存在")
    return project


@router.post("/{project_id}/briefing", response_model=ActionResult)
def submit_briefing(project_id: int, payload: EntryPayload) -> ActionResult:
    """报送施工交底；同一项目重复报送只留最新一版。"""
    entry, missing, message = service.submit_briefing(project_id, payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{project_id}/watch", response_model=ActionResult)
def add_watch(project_id: int, payload: EntryPayload) -> ActionResult:
    """补录一条旁站监护记录，台账视图上的监护记录条数同步刷新。"""
    entry, missing, message = service.add_watch(project_id, payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/watch/{watch_id}/close", response_model=ActionResult)
def close_watch(watch_id: int, payload: EntryPayload) -> ActionResult:
    """闭环一条违章监护记录；需要通过 project_id 指定所属项目。"""
    project_id = payload.values.get("project_id")
    try:
        project_id = int(project_id)
    except (TypeError, ValueError):
        return ActionResult(ok=False, message="缺少所属项目标识 project_id，无法闭环")
    entry, message = service.close_watch(project_id, watch_id)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{project_id}/finish", response_model=ActionResult)
def finish_project(project_id: int) -> ActionResult:
    """标注完工；存在未闭环违章监护记录时拒绝，完工后不再进入待监护视图。"""
    entry, message = service.finish_project(project_id)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)

"""第三方施工监护台账接口。

把外部单位在管网保护范围内的施工交底与旁站监护集中呈现：
- GET    /api/guard/projects            台账视图（默认仅在建，即待监护视图）
- GET    /api/guard/projects/{id}       项目明细（最新交底 + 每次旁站监护记录）
- POST   /api/guard/projects            登记施工项目
- POST   /api/guard/projects/{id}/briefing   报送/重复报送交底（只留最新一版）
- POST   /api/guard/projects/{id}/records    补录旁站监护记录
- POST   /api/guard/records/{id}/close       闭环违章监护记录
- POST   /api/guard/projects/{id}/complete   校验后标注完工
- GET    /api/guard/summary            台账统计（供运营概览核对）
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.guard import guard_service

router = APIRouter(prefix="/api/guard", tags=["第三方施工监护"])


@router.get("/projects", response_model=PageResult[dict])
def list_projects(
    keyword: str | None = Query(default=None, description="按项目名称、编号或外部单位检索"),
    scope: str = Query(default="pending", description="pending=待监护视图（仅在建），all=全部项目"),
    status: str | None = Query(default=None, description="scope=all 时可按 在建/已完工 筛选"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按施工项目列出交底时间、涉及管段、监护人与监护记录条数。"""
    if scope not in {"pending", "all"}:
        raise HTTPException(status_code=400, detail="scope 只支持 pending（待监护）或 all（全部）")
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = guard_service.list_projects(
        keyword=keyword, scope=scope, status=status, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/projects/{project_id}", response_model=dict)
def get_project(project_id: int) -> dict:
    """项目明细：最新一版交底与历次旁站监护记录。"""
    detail = guard_service.get_project_detail(project_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"施工项目 {project_id} 不存在或已归档")
    return detail


@router.post("/projects", response_model=ActionResult)
def create_project(payload: EntryPayload) -> ActionResult:
    """登记一个外部单位施工项目，初始为在建、尚未交底。"""
    project, missing = guard_service.create_project(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="施工项目已登记，进入待监护视图", entry=project)


@router.post("/projects/{project_id}/briefing", response_model=ActionResult)
def submit_briefing(project_id: int, payload: EntryPayload) -> ActionResult:
    """报送施工交底；同一项目重复报送时只保留最新一版。"""
    briefing, message = guard_service.submit_briefing(project_id, payload.values)
    if briefing is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=briefing)


@router.post("/projects/{project_id}/records", response_model=ActionResult)
def add_record(project_id: int, payload: EntryPayload) -> ActionResult:
    """补录一次旁站监护明细，台账视图上的监护记录条数随之同步更新。"""
    record, message = guard_service.add_record(project_id, payload.values)
    if record is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=record)


@router.post("/records/{record_id}/close", response_model=ActionResult)
def close_record(record_id: int, payload: EntryPayload | None = None) -> ActionResult:
    """闭环一条发现违章的旁站监护记录。"""
    record, message = guard_service.close_record(record_id)
    if record is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=record)


@router.post("/projects/{project_id}/complete", response_model=ActionResult)
def complete_project(project_id: int, payload: EntryPayload | None = None) -> ActionResult:
    """标注完工：有未闭环违章监护记录或尚未交底时拦下；完工后退出待监护视图。"""
    project, message = guard_service.complete_project(project_id)
    if project is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=project)


@router.get("/summary")
def summary() -> dict[str, int]:
    """台账统计：在建监护数与待监护视图条数一致，供运营概览核对。"""
    return guard_service.overview_summary()

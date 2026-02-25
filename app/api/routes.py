"""
ArcHeli v1.0.0 — API Routes  /v1/*
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class AgentRunReq(BaseModel):
    command: str
    source: str = "user"
    session_id: Optional[int] = None
    goal_id: Optional[int] = None
    context: dict = {}
    skill_hint: Optional[str] = None
    task_type: str = "general"
    budget: str = "medium"


class AgentRunResp(BaseModel):
    success: bool
    task_id: Optional[int]
    skill_used: Optional[str]
    model_used: Optional[str]
    output: Any
    tokens_used: int
    elapsed_s: float
    governor_approved: bool
    error: Optional[str] = None
    memory_hits: list = []


class GoalCreateReq(BaseModel):
    title: str
    description: str = ""
    priority: int = 5
    context: dict = {}


class GoalUpdateReq(BaseModel):
    progress: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None   # active|paused|completed|abandoned


class SkillInvokeReq(BaseModel):
    name: str
    inputs: dict = {}


class CronAddReq(BaseModel):
    name: str
    skill_name: str
    cron_expr: Optional[str] = None
    interval_s: Optional[int] = None
    input_data: dict = {}
    governor_required: bool = True


class SessionCreateReq(BaseModel):
    name: str
    context: dict = {}


class MemoryAddReq(BaseModel):
    content: str
    source: str = "user"
    tags: list[str] = []
    importance: float = 0.5
    metadata: dict = {}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["system"])
async def health():
    from ..utils.model_router import model_router
    from ..runtime.skill_manager import skill_manager
    from ..runtime.cron import cron_system
    return {
        "status": "ok",
        "system": "ArcHeli",
        "version": "1.0.0",
        "ai_providers": model_router.list_providers(),
        "loaded_skills": [s["name"] for s in skill_manager.list_skills()],
        "cron_active": cron_system._started,
    }


@router.get("/models", tags=["system"])
async def list_models():
    from ..utils.model_router import model_router
    return {"providers": model_router.list_providers(),
            "available": model_router.available_providers()}


# ── Agent (OODA) ──────────────────────────────────────────────────────────────

@router.post("/agent/run", response_model=AgentRunResp, tags=["agent"])
async def agent_run(req: AgentRunReq):
    """Execute one full OODA cycle: Observe → Orient → Decide → Act → Learn"""
    try:
        from ..loop.main_loop import main_loop, LoopInput
        result = main_loop.run(LoopInput(
            command=req.command, source=req.source,
            session_id=req.session_id, goal_id=req.goal_id,
            context=req.context, skill_hint=req.skill_hint,
            task_type=req.task_type, budget=req.budget,
        ))
        return AgentRunResp(
            success=result.success, task_id=result.task_id,
            skill_used=result.skill_used, model_used=result.model_used,
            output=result.output, tokens_used=result.tokens_used,
            elapsed_s=result.elapsed_s, governor_approved=result.governor_approved,
            error=result.error, memory_hits=result.memory_hits,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/agent/tasks", tags=["agent"])
async def list_tasks(limit: int = 20):
    from ..runtime.lifecycle import lifecycle
    return {"tasks": lifecycle.tasks.list_recent(limit)}


@router.get("/agent/tasks/{task_id}", tags=["agent"])
async def get_task(task_id: int):
    from ..runtime.lifecycle import lifecycle
    t = lifecycle.tasks.get(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills", tags=["skills"])
async def list_skills():
    from ..runtime.skill_manager import skill_manager
    return {"skills": skill_manager.list_skills()}


@router.post("/skills/invoke", tags=["skills"])
async def invoke_skill(req: SkillInvokeReq):
    from ..runtime.skill_manager import skill_manager, SkillNotFound
    try:
        return skill_manager.invoke(req.name, req.inputs)
    except SkillNotFound as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", tags=["goals"])
async def list_goals(status: Optional[str] = None):
    from ..loop.goal_tracker import goal_tracker
    return {"goals": goal_tracker.list_active() if status == "active"
            else goal_tracker.list_all()}


@router.post("/goals", tags=["goals"])
async def create_goal(req: GoalCreateReq):
    from ..loop.goal_tracker import goal_tracker
    gid = goal_tracker.create(req.title, req.description,
                               req.priority, req.context)
    return {"goal_id": gid}


@router.patch("/goals/{goal_id}", tags=["goals"])
async def update_goal(goal_id: int, req: GoalUpdateReq):
    from ..loop.goal_tracker import goal_tracker
    g = goal_tracker.get(goal_id)
    if not g:
        raise HTTPException(404, "Goal not found")
    if req.progress is not None:
        goal_tracker.update_progress(goal_id, req.progress, req.notes)
    if req.status == "paused":    goal_tracker.pause(goal_id)
    elif req.status == "active":  goal_tracker.resume(goal_id)
    elif req.status == "abandoned": goal_tracker.abandon(goal_id)
    elif req.status == "completed": goal_tracker.complete(goal_id)
    return goal_tracker.get(goal_id)


@router.delete("/goals/{goal_id}", tags=["goals"])
async def delete_goal(goal_id: int):
    from ..loop.goal_tracker import goal_tracker
    goal_tracker.abandon(goal_id)
    return {"status": "abandoned", "goal_id": goal_id}


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", tags=["sessions"])
async def list_sessions():
    from ..runtime.lifecycle import lifecycle
    return {"sessions": lifecycle.sessions.list_active()}


@router.post("/sessions", tags=["sessions"])
async def create_session(req: SessionCreateReq):
    from ..runtime.lifecycle import lifecycle
    sid = lifecycle.sessions.create(req.name, req.context)
    return {"session_id": sid}


@router.delete("/sessions/{session_id}", tags=["sessions"])
async def end_session(session_id: int):
    from ..runtime.lifecycle import lifecycle
    lifecycle.sessions.end(session_id)
    return {"status": "ended", "session_id": session_id}


# ── Memory ────────────────────────────────────────────────────────────────────

@router.get("/memory/search", tags=["memory"])
async def search_memory(q: str, top_k: int = 5):
    from ..memory.store import memory_store
    return {"results": memory_store.query(q, top_k=top_k)}


@router.post("/memory", tags=["memory"])
async def add_memory(req: MemoryAddReq):
    from ..memory.store import memory_store
    mid = memory_store.add(req.content, req.source, req.tags,
                            req.importance, req.metadata)
    return {"memory_id": mid}


@router.get("/memory/recent", tags=["memory"])
async def recent_memory(limit: int = 10):
    from ..memory.store import memory_store
    return {"items": memory_store.get_recent(limit)}


# ── Cron ──────────────────────────────────────────────────────────────────────

@router.get("/cron", tags=["cron"])
async def list_cron():
    from ..runtime.cron import cron_system
    return {"jobs": cron_system.list_jobs()}


@router.post("/cron", tags=["cron"])
async def add_cron(req: CronAddReq):
    from ..runtime.cron import cron_system
    try:
        if req.cron_expr:
            return cron_system.add_cron(req.name, req.cron_expr, req.skill_name,
                                        req.input_data, req.governor_required)
        elif req.interval_s:
            return cron_system.add_interval(req.name, req.interval_s, req.skill_name,
                                            req.input_data, req.governor_required)
        raise HTTPException(400, "cron_expr or interval_s required")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/cron/{name}/trigger", tags=["cron"])
async def trigger_cron(name: str):
    from ..runtime.cron import cron_system
    try:
        return cron_system.trigger_now(name)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/cron/{name}", tags=["cron"])
async def remove_cron(name: str):
    from ..runtime.cron import cron_system
    cron_system.remove(name)
    return {"status": "removed", "name": name}

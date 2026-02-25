"""
ArcHeli v1.0.0 — Database Schema
Single SQLite file: all tables in one place, NullPool for SQLite safety.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text,
    create_engine, event
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool


def _make_engine():
    from ..config import settings
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )


engine = _make_engine()


@event.listens_for(engine, "connect")
def _set_pragmas(conn, _):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ── Sessions ──────────────────────────────────────────────────────────────────

class AHSession(Base):
    __tablename__ = "ah_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(128), nullable=False)
    status     = Column(String(32), default="active")
    context    = Column(Text, default="{}")
    goal_ids   = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Tasks ─────────────────────────────────────────────────────────────────────

class AHTask(Base):
    __tablename__ = "ah_tasks"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, nullable=True)
    title        = Column(String(256), nullable=False)
    skill_name   = Column(String(128), nullable=True)
    task_type    = Column(String(64), default="general")
    status       = Column(String(32), default="created")
    # created|assigned|executing|verifying|closed|failed
    input_data   = Column(Text, default="{}")
    output_data  = Column(Text, default="{}")
    governor_ok  = Column(Boolean, default=False)
    model_used   = Column(String(64), nullable=True)
    tokens_used  = Column(Integer, default=0)
    error_msg    = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at    = Column(DateTime, nullable=True)


# ── Agents ────────────────────────────────────────────────────────────────────

class AHAgent(Base):
    __tablename__ = "ah_agents"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    session_id    = Column(Integer, nullable=True)
    agent_type    = Column(String(64), default="general")
    status        = Column(String(32), default="idle")
    current_task  = Column(Integer, nullable=True)
    metadata_     = Column(Text, default="{}")
    created_at    = Column(DateTime, default=datetime.utcnow)
    terminated_at = Column(DateTime, nullable=True)


# ── Goals ─────────────────────────────────────────────────────────────────────

class AHGoal(Base):
    __tablename__ = "ah_goals"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(256), nullable=False)
    description = Column(Text, default="")
    status      = Column(String(32), default="active")
    # active|paused|completed|abandoned
    progress    = Column(Float, default=0.0)
    priority    = Column(Integer, default=5)
    context     = Column(Text, default="{}")
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Skills ────────────────────────────────────────────────────────────────────

class AHSkill(Base):
    __tablename__ = "ah_skills"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(128), unique=True, nullable=False)
    version      = Column(String(32), default="1.0")
    description  = Column(Text, default="")
    manifest     = Column(Text, default="{}")
    source       = Column(String(32), default="local")
    enabled      = Column(Boolean, default=True)
    invoke_count = Column(Integer, default=0)
    error_count  = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Cron Jobs ─────────────────────────────────────────────────────────────────

class AHCronJob(Base):
    __tablename__ = "ah_cron_jobs"
    id                = Column(Integer, primary_key=True, autoincrement=True)
    name              = Column(String(128), unique=True, nullable=False)
    cron_expr         = Column(String(64), nullable=True)
    interval_s        = Column(Integer, nullable=True)
    skill_name        = Column(String(128), nullable=False)
    input_data        = Column(Text, default="{}")
    enabled           = Column(Boolean, default=True)
    governor_required = Column(Boolean, default=True)
    last_run          = Column(DateTime, nullable=True)
    next_run          = Column(DateTime, nullable=True)
    run_count         = Column(Integer, default=0)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Browser Sessions ──────────────────────────────────────────────────────────

class AHBrowserSession(Base):
    __tablename__ = "ah_browser_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    task_id    = Column(Integer, nullable=True)
    url        = Column(Text, nullable=True)
    status     = Column(String(32), default="active")
    actions    = Column(Text, default="[]")
    screenshot = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at  = Column(DateTime, nullable=True)


# ── Memory Items ──────────────────────────────────────────────────────────────

class AHMemory(Base):
    """Lightweight semantic memory — keyword-searchable, no vector DB required."""
    __tablename__ = "ah_memory"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    content    = Column(Text, nullable=False)
    source     = Column(String(64), default="archeli")
    tags       = Column(Text, default="[]")     # JSON list of strings
    importance = Column(Float, default=0.5)     # 0.0–1.0
    metadata_  = Column(Text, default="{}")     # JSON
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Governor Audit Log ────────────────────────────────────────────────────────

class AHAuditLog(Base):
    __tablename__ = "ah_audit_log"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    action     = Column(String(256), nullable=False)
    decision   = Column(String(16), nullable=False)   # APPROVED|BLOCKED|WARNED
    risk_score = Column(Integer, default=0)
    reason     = Column(Text, nullable=True)
    context    = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
ArcHeli v1.0.0 — Configuration
Standalone autonomous AI system.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "ArcHeli"
    app_version: str = "1.0.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────────────────────────────────
    db_path: str = "./archeli.db"

    # ── AI Providers ─────────────────────────────────────────────────────────
    # Set any key to enable that provider automatically.

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # OpenAI-compatible
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Google Gemini
    google_api_key: str = ""

    # Groq (ultra-fast inference)
    groq_api_key: str = ""

    # Mistral
    mistral_api_key: str = ""

    # OLLAMA local model  (OLLAMA_ENABLED=true to activate)
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_default_model: str = "llama3.2"

    # Custom OpenAI-compatible endpoint (LM Studio / DeepSeek / Together / etc.)
    custom_model_base_url: str = ""
    custom_model_api_key: str = ""
    custom_model_name: str = "custom"

    # ── Routing ───────────────────────────────────────────────────────────────
    routing_rules_path: str = "./configs/routing_rules.yaml"

    # ── Governor ──────────────────────────────────────────────────────────────
    governor_mode: str = "soft_block"   # soft_block | hard_block | audit_only | off
    risk_block_threshold: int = 90
    risk_warn_threshold: int = 70

    # ── Paths ─────────────────────────────────────────────────────────────────
    skills_dir: str = "./app/skills"
    evidence_dir: str = "./evidence"
    cron_timezone: str = "Asia/Taipei"

    # ── Security ──────────────────────────────────────────────────────────────
    api_key: str = ""          # Required for /v1/* endpoints (empty = no auth)
    admin_token: str = ""

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

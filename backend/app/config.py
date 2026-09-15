"""Centralized configuration — all tuneable parameters in one place.

Loads from environment variables (or a .env file) with sensible defaults.
The gate thresholds, API keys, and database URL are all here so that:
  - benchmark sweeps can test different thresholds without code changes
  - the mock → real backend swap only requires changing env vars, not source
  - every config value is logged alongside results for reproducibility
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"
# Uvicorn can be launched from either the repository root or backend/. Resolve
# the project environment once rather than relying on the process CWD.
load_dotenv(_ENV_FILE)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App-wide settings, loaded from env vars (prefix: none, flat names)."""

    # --- Gate thresholds (re-derive empirically when swapping to real classifier) ---
    gate_min_classification_confidence: float = 0.70
    gate_min_entity_confidence: float = 0.60
    gate_max_clarification_rounds: int = 3

    # --- Database ---
    database_url: str = "postgresql://sauticivic:sauticivic@localhost:5432/sauticivic"

    # --- ASR API keys (required for real ASR, not for mock pipeline) ---
    sahara_api_key: str = ""
    sahara_api_url: str = "https://infer.voice.intron.io/file/v1/upload/sync"
    deepgram_api_key: str = ""
    gemini_api_key: str = ""
    whisper_model_size: str = "large-v3"

    # --- Optional DeepSeek drafting / clarification layer ---
    # Never expose this value to browser code. The deterministic gate remains
    # authoritative even when this integration is enabled.
    deepseek_api_key: str = ""
    deepseek_api_url: str = "https://api.deepseek.com/chat/completions"
    deepseek_timeout_seconds: float = 10.0
    deepseek_max_retries: int = 1

    # --- Benchmark runner ---
    benchmark_clip_delay_ms: int = 200

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = {"env_file": _ENV_FILE, "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton — import this from anywhere.
settings = Settings()

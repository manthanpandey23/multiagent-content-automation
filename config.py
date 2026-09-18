"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=False)


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _get_bool(key: str, default: bool = False) -> bool:
    return _get(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _get_float(key: str, default: float) -> float:
    try:
        return float(_get(key, str(default)))
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


class Config:
    # NVIDIA NIM
    nvidia_api_key: str = _get("NVIDIA_API_KEY")
    nvidia_model: str = _get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
    nvidia_base_url: str = _get("NVIDIA_BASE_URL", "https://api.nvidia.com/v1")

    # OpenRouter
    openrouter_api_key: str = _get("OPENROUTER_API_KEY")
    openrouter_model: str = _get("OPENROUTER_MODEL", "google/gemma-2-9b-it")
    openrouter_base_url: str = _get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # Telegram
    telegram_bot_token: str = _get("TELEGRAM_BOT_TOKEN")
    telegram_admin_chat_id: str = _get("TELEGRAM_ADMIN_CHAT_ID")

    # Database
    postgres_user: str = _get("POSTGRES_USER", "agent")
    postgres_password: str = _get("POSTGRES_PASSWORD", "agent_password")
    postgres_db: str = _get("POSTGRES_DB", "social_agent")
    postgres_host: str = _get("POSTGRES_HOST", "localhost")
    postgres_port: int = _get_int("POSTGRES_PORT", 5433)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = _get("REDIS_HOST", "localhost")
    redis_port: int = _get_int("REDIS_PORT", 6380)

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # Pipeline
    pipeline_categories: list[str] = _get(
        "PIPELINE_CATEGORIES",
        "AI,Machine Learning,IT Sector,Automation,Cloud Computing,Cybersecurity,Software Engineering,Developer Tools,AI Agents,Generative AI,LLM",
    ).split(",")
    title_max_words: int = _get_int("PIPELINE_TITLE_MAX_WORDS", 100)
    desc_max_words: int = _get_int("PIPELINE_DESC_MAX_WORDS", 300)
    min_quality_score: float = _get_float("PIPELINE_MIN_QUALITY_SCORE", 75)
    research_hour: int = _get_int("PIPELINE_RESEARCH_HOUR", 9)
    research_minute: int = _get_int("PIPELINE_RESEARCH_MINUTE", 0)
    publish_hour: int = _get_int("PIPELINE_PUBLISH_HOUR", 10)
    publish_minute: int = _get_int("PIPELINE_PUBLISH_MINUTE", 0)
    pipeline_timezone: str = _get("PIPELINE_TIMEZONE", "Asia/Kolkata")
    daily_limit: int = _get_int("PIPELINE_DAILY_LIMIT", 5000)

    # Guardian
    guardian_enabled: bool = _get_bool("GUARDIAN_ENABLED", True)
    guardian_severity: str = _get("GUARDIAN_SEVERITY", "warn")
    guardian_alert_immediate: bool = _get_bool("GUARDIAN_ALERT_IMMEDIATE", True)
    guardian_token_budget: int = _get_int("GUARDIAN_TOKEN_BUDGET_PER_AGENT", 500000)

    # Evaluation
    eval_enabled: bool = _get_bool("EVAL_ENABLED", True)
    eval_run_after_each: bool = _get_bool("EVAL_RUN_AFTER_EACH_PIPELINE", True)
    eval_daily_hour: int = _get_int("EVAL_DAILY_REPORT_HOUR", 22)
    eval_weekly_day: str = _get("EVAL_WEEKLY_REPORT_DAY", "sunday")
    eval_weekly_hour: int = _get_int("EVAL_WEEKLY_REPORT_HOUR", 23)
    eval_monthly_day: str = _get("EVAL_MONTHLY_REPORT_DAY", "last")
    eval_monthly_hour: int = _get_int("EVAL_MONTHLY_REPORT_HOUR", 23)

    # UI
    ui_enabled: bool = _get_bool("UI_ENABLED", True)
    ui_port: int = _get_int("UI_PORT", 8501)
    ui_auto_refresh: int = _get_int("UI_AUTO_REFRESH_SECONDS", 30)
    ui_host: str = _get("UI_HOST", "0.0.0.0")

    # Social
    instagram_access_token: str = _get("INSTAGRAM_ACCESS_TOKEN")
    instagram_app_id: str = _get("INSTAGRAM_APP_ID")
    linkedin_access_token: str = _get("LINKEDIN_ACCESS_TOKEN")
    linkedin_app_id: str = _get("LINKEDIN_APP_ID")
    twitter_api_key: str = _get("TWITTER_API_KEY")
    twitter_api_secret: str = _get("TWITTER_API_SECRET")
    twitter_access_token: str = _get("TWITTER_ACCESS_TOKEN")
    twitter_access_secret: str = _get("TWITTER_ACCESS_SECRET")

    # Feature flags
    auto_run: bool = _get_bool("AUTO_RUN", True)
    dry_run: bool = _get_bool("DRY_RUN", False)

    # Token Manager
    token_manager_enabled: bool = _get_bool("TOKEN_MANAGER_ENABLED", True)
    token_safety_margin: float = _get_float("TOKEN_SAFETY_MARGIN", 1.2)
    token_budget_default: int = _get_int("TOKEN_BUDGET_DEFAULT", 500000)
    token_budget_warning: float = _get_float("TOKEN_BUDGET_WARNING", 0.80)
    token_budget_critical: float = _get_float("TOKEN_BUDGET_CRITICAL", 0.95)
    token_context_warning: float = _get_float("TOKEN_CONTEXT_WARNING", 0.70)
    token_cache_ttl_hours: int = _get_int("TOKEN_CACHE_TTL_HOURS", 1)
    token_cache_ttl_long: int = _get_int("TOKEN_CACHE_TTL_LONG", 24)
    token_cache_enabled: bool = _get_bool("TOKEN_CACHE_ENABLED", True)
    token_caching_enabled: bool = _get_bool("TOKEN_CACHING_ENABLED", True)
    token_provider_switch_auto: bool = _get_bool("TOKEN_PROVIDER_SWITCH_AUTO", True)
    token_min_model_fallback: str = _get("TOKEN_MIN_MODEL_FALLBACK", "2B")

    @property
    def primary_provider(self) -> str:
        return "nvidia"

    @property
    def fallback_provider(self) -> str:
        return "openrouter"


CONFIG = Config()

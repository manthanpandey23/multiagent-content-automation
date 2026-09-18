"""Scheduled task definitions using APScheduler.

Schedule (IST = UTC+5:30):
  0 9  * * *  -> Agent 1 fetch news + review -> Telegram human review
  0 10 * * *  -> Agents 2-4 create/validate/publish (if approvals given)
"""

from __future__ import annotations

from typing import Callable, Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:  # pragma: no cover
    AsyncIOScheduler = None  # type: ignore

from config import CONFIG
from utils.logger import get_logger

log = get_logger("scheduler")

scheduler: Optional[AsyncIOScheduler] = None

_app_runner: Optional[Callable] = None


def register_dependencies(app_runner: Callable[[str, Optional[str]], None]) -> None:
    """Inject the orchestrator's async runner so jobs can invoke the pipeline."""
    global _app_runner
    _app_runner = app_runner


def _make_scheduler() -> AsyncIOScheduler:
    if AsyncIOScheduler is None:  # pragma: no cover
        raise RuntimeError("APScheduler not installed")
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(CONFIG.pipeline_timezone)
    sched = AsyncIOScheduler(timezone=tz)
    return sched


async def daily_news_fetch() -> None:
    """9 AM IST: Fetch news via Agent 1."""
    if _app_runner is None:
        log.warning("no_app_runner_registered")
        return
    log.info("scheduled_news_fetch_triggered")
    _app_runner("research", None)


async def daily_publish() -> None:
    """10 AM IST: Create, validate, and publish content."""
    if _app_runner is None:
        log.warning("no_app_runner_registered")
        return
    log.info("scheduled_publish_triggered")
    _app_runner("create_and_publish", None)


def start_scheduler() -> Optional[AsyncIOScheduler]:
    """Start the APScheduler with daily jobs.  No-op if AUTO_RUN is false."""
    if not CONFIG.auto_run:
        log.info("scheduler_disabled_auto_run_false")
        return None
    from datetime import datetime, timedelta

    global scheduler
    scheduler = _make_scheduler()

    now = datetime.now()
    ist_offset = 5.5
    target_research = now.replace(
        hour=CONFIG.research_hour, minute=CONFIG.research_minute, second=0, microsecond=0
    )
    if target_research <= now:
        target_research += timedelta(days=1)

    scheduler.add_job(
        daily_news_fetch,
        "cron",
        hour=CONFIG.research_hour,
        minute=CONFIG.research_minute,
        timezone="Asia/Kolkata",
        id="daily_news_fetch",
        replace_existing=True,
    )
    scheduler.add_job(
        daily_publish,
        "cron",
        hour=CONFIG.publish_hour,
        minute=CONFIG.publish_minute,
        timezone="Asia/Kolkata",
        id="daily_publish",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler_started", research_hour=CONFIG.research_hour, publish_hour=CONFIG.publish_hour)
    return scheduler


def shutdown_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        log.info("scheduler_shutdown")

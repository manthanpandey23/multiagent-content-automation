#!/usr/bin/env python
"""Entry point — starts the orchestrator, scheduler, Telegram bot, and UI.

Usage:
    python run.py            # full pipeline (orchestrator + scheduler + telegram)
    python run.py --ui       # also launch Streamlit dashboard
    python run.py --once     # run a single full pipeline pass (no scheduler)
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from config import CONFIG
from utils.logger import get_logger
from db.connection import init_db, ping as db_ping
from scheduler.tasks import start_scheduler, shutdown_scheduler, register_dependencies
from pipeline import PipelineOrchestrator
from integrations.telegram_bot import TelegramBot

log = get_logger("run")


def _check_database() -> bool:
    if db_ping():
        init_db()
        log.info("database_ready")
        return True
    log.warning("database_unavailable_redis_fallback")
    return False


def _check_redis() -> bool:
    try:
        import redis

        r = redis.from_url(CONFIG.redis_url, decode_responses=True)
        r.ping()
        log.info("redis_ready")
        return True
    except Exception as exc:
        log.warning("redis_unavailable", error=str(exc))
        return False


async def _run_once(orchestrator: PipelineOrchestrator) -> None:
    await orchestrator.run_stage("create_and_publish")


async def _run_service(orchestrator: PipelineOrchestrator, with_ui: bool = False) -> None:
    register_dependencies(lambda stage, sid: asyncio.create_task(
        orchestrator.run_stage(stage, sid)
    ))
    if CONFIG.telegram_bot_token and CONFIG.telegram_bot_token != "your_telegram_bot_token":
        bot = TelegramBot()
        bot.set_orchestrator_callback(orchestrator.handle_telegram_command)
        app = bot.build_application()
        if app:
            orchestrator.telegram = bot
            log.info("telegram_bot_started")
            asyncio.create_task(app.run_polling())
    else:
        log.warning("telegram_bot_token_not_configured")

    sched = start_scheduler()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        shutdown_scheduler()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes Social Agent")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--once", action="store_true", help="Run a single pipeline pass")
    args = parser.parse_args()

    _check_database()
    _check_redis()

    orchestrator = PipelineOrchestrator()

    if args.once:
        asyncio.run(_run_once(orchestrator))
        return

    if args.ui:
        import subprocess

        try:
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "ui/app.py",
                 f"--server.port={CONFIG.ui_port}"],
                cwd=sys.path[0] or ".",
            )
            log.info("streamlit_started", port=CONFIG.ui_port)
        except Exception as exc:
            log.error("streamlit_start_failed", error=str(exc))

    asyncio.run(_run_service(orchestrator, with_ui=args.ui))


if __name__ == "__main__":
    main()

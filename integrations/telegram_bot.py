"""Telegram bot integration for control, review, and alerts."""

from __future__ import annotations

from typing import Optional, Callable, Awaitable, Any

from config import CONFIG
from utils.logger import get_logger

log = get_logger("telegram_bot")

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        CallbackQueryHandler,
    )
    _HAS_TELEGRAM = True
except ImportError:  # pragma: no cover
    _HAS_TELEGRAM = False
    Application = None  # type: ignore


class TelegramBot:
    """Manages the Telegram bot: commands, review workflow, and alerts."""

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or CONFIG.telegram_bot_token
        self.chat_id: Optional[int] = CONFIG.telegram_admin_chat_id or None
        if self.chat_id and str(self.chat_id).isdigit():
            self.chat_id = int(self.chat_id)
        self.application: Optional[Any] = None
        self._handlers: dict[str, Callable] = {}
        self._orchestrator_callback: Optional[Callable] = None

    def set_orchestrator_callback(self, callback: Callable[[str, dict], Awaitable[None]]) -> None:
        """Register a callback so Telegram commands can trigger pipeline actions."""
        self._orchestrator_callback = callback

    async def send_message(self, message: str, chat_id: Optional[int] = None) -> None:
        if not self.token or self.token == "your_telegram_bot_token":
            log.warning("telegram_not_configured", message=message)
            return
        if not _HAS_TELEGRAM:
            return
        if self.application is None:
            return
        target = chat_id or self.chat_id
        if target is None:
            return
        try:
            await self.application.bot.send_message(chat_id=target, text=message)
        except Exception as exc:
            log.warning("telegram_send_failed", error=str(exc))

    def build_application(self) -> Any:
        if not _HAS_TELEGRAM:
            log.warning("telegram_lib_unavailable")
            return None
        if not self.token or self.token == "your_telegram_bot_token":
            log.warning("telegram_token_not_set")
            return None
        self.application = Application.builder().token(self.token).build()
        self._register_handlers()
        return self.application

    def _register_handlers(self) -> None:
        assert self.application is not None
        commands = {
            "start": self._cmd_start,
            "pipeline": self._cmd_pipeline_status,
            "news": self._cmd_news,
            "create": self._cmd_create,
            "validate": self._cmd_validate,
            "publish": self._cmd_publish,
            "run": self._cmd_run_all,
            "review": self._cmd_review,
            "approve": self._cmd_approve,
            "reject": self._cmd_reject,
            "edit": self._cmd_edit,
            "history": self._cmd_history,
            "config": self._cmd_config,
            "set": self._cmd_set,
            "dryrun": self._cmd_dryrun,
            "guardian": self._cmd_guardian,
            "eval": self._cmd_eval,
            "dashboard": self._cmd_dashboard,
            "agents": self._cmd_agents,
            "tokens": self._cmd_tokens,
            "providers": self._cmd_providers,
            "switch": self._cmd_switch,
        }
        for cmd, handler in commands.items():
            self.application.add_handler(CommandHandler(cmd, handler))
        self.application.add_handler(CallbackQueryHandler(self._callback_query))

    async def _handle_command(self, cmd: str, update: Any, context: Any) -> None:
        if self._orchestrator_callback is None:
            await self._reply(update, f"Command /{cmd} received but orchestrator not connected.")
            return
        await self._orchestrator_callback(cmd, {"update": update, "context": context})

    async def _reply(self, update: Any, text: str) -> None:
        await update.effective_message.reply_text(text)

    async def _cmd_start(self, update: Any, context: Any) -> None:
        await self._reply(update, self._welcome_message())

    def _welcome_message(self) -> str:
        return (
            "🤖 Hermes Social Agent — ready!\n\n"
            "Commands:\n"
            "/pipeline status — current pipeline stage\n"
            "/news — fetch tech news\n"
            "/create — create social content\n"
            "/validate — validate content\n"
            "/publish — publish content\n"
            "/run all — full pipeline\n"
            "/review — pending review items\n"
            "/approve <id> — approve item\n"
            "/reject <id> <reason> — reject item\n"
            "/edit <id> <text> — suggest edits\n"
            "/history — pipeline history\n"
            "/guardian — Guardian status/alerts\n"
            "/tokens — token usage & budgets\n"
            "/providers — provider status\n"
            "/switch <agent> <provider/model> — manual switch\n"
            "/agents — agent status\n"
            "/eval status|report <period>\n"
            "/dashboard — UI link\n"
            "/dryrun — toggle dry-run mode\n"
        )

    async def _cmd_pipeline_status(self, update: Any, context: Any) -> None:
        await self._handle_command("pipeline status", update, context)

    async def _cmd_news(self, update: Any, context: Any) -> None:
        await self._handle_command("news", update, context)

    async def _cmd_create(self, update: Any, context: Any) -> None:
        await self._handle_command("create", update, context)

    async def _cmd_validate(self, update: Any, context: Any) -> None:
        await self._handle_command("validate", update, context)

    async def _cmd_publish(self, update: Any, context: Any) -> None:
        await self._handle_command("publish", update, context)

    async def _cmd_run_all(self, update: Any, context: Any) -> None:
        await self._handle_command("run all", update, context)

    async def _cmd_review(self, update: Any, context: Any) -> None:
        await self._handle_command("review", update, context)

    async def _cmd_approve(self, update: Any, context: Any) -> None:
        await self._handle_command("approve", update, context)

    async def _cmd_reject(self, update: Any, context: Any) -> None:
        await self._handle_command("reject", update, context)

    async def _cmd_edit(self, update: Any, context: Any) -> None:
        await self._handle_command("edit", update, context)

    async def _cmd_history(self, update: Any, context: Any) -> None:
        await self._handle_command("history", update, context)

    async def _cmd_config(self, update: Any, context: Any) -> None:
        lines = [
            "⚙️ Configuration:",
            f"  Categories: {', '.join(CONFIG.pipeline_categories)}",
            f"  Pipeline: {CONFIG.research_hour}:00 / {CONFIG.publish_hour}:00 IST",
            f"  Dry-run: {CONFIG.dry_run}",
            f"  Auto-run: {CONFIG.auto_run}",
            f"  Guardian: {CONFIG.guardian_enabled}",
            f"  Eval: {CONFIG.eval_enabled}",
            f"  UI: {CONFIG.ui_enabled} (port {CONFIG.ui_port})",
        ]
        await self._reply(update, "\n".join(lines))

    async def _cmd_set(self, update: Any, context: Any) -> None:
        await self._handle_command("set", update, context)

    async def _cmd_dryrun(self, update: Any, context: Any) -> None:
        CONFIG.dry_run = not CONFIG.dry_run
        await self._reply(update, f"Dry-run mode: {CONFIG.dry_run}")

    async def _cmd_guardian(self, update: Any, context: Any) -> None:
        await self._handle_command("guardian", update, context)

    async def _cmd_eval(self, update: Any, context: Any) -> None:
        await self._handle_command("eval", update, context)

    async def _cmd_dashboard(self, update: Any, context: Any) -> None:
        await self._reply(update, f"🔗 Dashboard: http://localhost:{CONFIG.ui_port}")

    async def _cmd_agents(self, update: Any, context: Any) -> None:
        await self._handle_command("agents", update, context)

    async def _cmd_tokens(self, update: Any, context: Any) -> None:
        await self._handle_command("tokens", update, context)

    async def _cmd_providers(self, update: Any, context: Any) -> None:
        await self._handle_command("providers", update, context)

    async def _cmd_switch(self, update: Any, context: Any) -> None:
        await self._handle_command("switch", update, context)

    async def _callback_query(self, update: Any, context: Any) -> None:
        await self._handle_command("callback_query", update, context)

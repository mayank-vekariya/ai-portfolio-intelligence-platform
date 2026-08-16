from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import BotCommand, Chat, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from portfolio_bot.config import ConfigurationError, Settings, parse_clock
from portfolio_bot.database import Database, UserRecord
from portfolio_bot.market_data import normalize_ticker
from portfolio_bot.services import PortfolioService, money

LOGGER = logging.getLogger(__name__)


HELP_TEXT = """📌 COMMANDS

/add TICKER SHARES AVG_COST - add shares; combines with an existing lot
/set TICKER SHARES AVG_COST - replace the tracked position
/remove TICKER - remove a position
/cash AMOUNT - set tracked portfolio cash
/portfolio - current summary
/risk - concentration and review alerts
/brief - generate the daily brief now
/analyze TICKER - technical context, not a trade instruction
/watch TICKER - add to watchlist
/unwatch TICKER - remove from watchlist
/watchlist - latest watched prices
/tip - one portfolio habit
/daily HH:MM TIMEZONE - schedule a brief, e.g. /daily 07:30 America/Los_Angeles
/daily off - pause automatic briefs
/settings - show current settings
/id - show your Telegram user ID for the private-beta allowlist
/privacy - data and safety information
/delete_me CONFIRM - delete your stored bot data
/help - show this list

This MVP cannot connect to a broker or place an order."""


class PortfolioTelegramBot:
    def __init__(self, settings: Settings, database: Database, service: PortfolioService) -> None:
        self.settings = settings
        self.database = database
        self.service = service

    def build_application(self) -> Application:
        application = (
            ApplicationBuilder()
            .token(self.settings.telegram_bot_token)
            .post_init(self.post_init)
            .build()
        )
        handlers = {
            "start": self.start,
            "help": self.help,
            "add": self.add,
            "set": self.set_holding,
            "remove": self.remove,
            "cash": self.cash,
            "portfolio": self.portfolio,
            "risk": self.risk,
            "brief": self.brief,
            "analyze": self.analyze,
            "watch": self.watch,
            "unwatch": self.unwatch,
            "watchlist": self.watchlist,
            "tip": self.tip,
            "daily": self.daily,
            "settings": self.show_settings,
            "id": self.show_id,
            "privacy": self.privacy,
            "delete_me": self.delete_me,
        }
        for command, callback in handlers.items():
            application.add_handler(CommandHandler(command, callback))
        application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
        application.add_error_handler(self.error_handler)
        return application

    async def post_init(self, application: Application) -> None:
        commands = [
            BotCommand("portfolio", "Show tracked portfolio"),
            BotCommand("brief", "Generate today's portfolio brief"),
            BotCommand("risk", "Show portfolio review alerts"),
            BotCommand("analyze", "Analyze a ticker"),
            BotCommand("add", "Add shares to a holding"),
            BotCommand("set", "Replace a holding"),
            BotCommand("cash", "Set tracked cash"),
            BotCommand("watch", "Add ticker to watchlist"),
            BotCommand("watchlist", "Show watchlist"),
            BotCommand("daily", "Configure automatic brief"),
            BotCommand("tip", "Show a portfolio habit"),
            BotCommand("help", "Show all commands"),
        ]
        await application.bot.set_my_commands(commands)
        for user in self.database.list_active_users():
            self._schedule_user(application, user)

    async def _authorize(self, update: Update) -> int | None:
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message
        if user is None or chat is None or message is None:
            return None
        if chat.type != Chat.PRIVATE:
            await message.reply_text("For privacy, use this bot only in a direct private chat.")
            return None
        if self.settings.allowed_user_ids and user.id not in self.settings.allowed_user_ids:
            await message.reply_text("This private beta is not enabled for your Telegram account.")
            return None
        display_name = user.full_name or user.username or str(user.id)
        self.database.register_user(
            telegram_user_id=user.id,
            chat_id=chat.id,
            display_name=display_name,
            timezone=self.settings.default_timezone,
            daily_brief_time=self.settings.default_daily_brief_time,
        )
        return user.id

    @staticmethod
    def _positive_decimal(raw: str, label: str, allow_zero: bool = False) -> Decimal:
        try:
            value = Decimal(raw.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError(f"{label} must be a number") from exc
        if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
            qualifier = "zero or greater" if allow_zero else "greater than zero"
            raise ValueError(f"{label} must be {qualifier}")
        return value

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._authorize(update) is None:
            return
        await update.effective_message.reply_text(
            "Welcome to the private Portfolio Brief MVP.\n\n"
            "Start by adding a position:\n/add AAPL 10 185.50\n\n"
            "Then run /portfolio or /brief.\n\n" + HELP_TEXT
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._authorize(update) is not None:
            await update.effective_message.reply_text(HELP_TEXT)

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 3:
            await update.effective_message.reply_text("Usage: /add AAPL 10 185.50")
            return
        try:
            ticker = normalize_ticker(context.args[0])
            quantity = self._positive_decimal(context.args[1], "Shares")
            average_cost = self._positive_decimal(context.args[2], "Average cost", allow_zero=True)
            holding = self.database.add_holding(user_id, ticker, quantity, average_cost)
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(
            f"Saved {format(holding.quantity.normalize(), 'f')} {ticker} shares at a combined "
            "average cost "
            f"of {money(holding.average_cost)}."
        )

    async def set_holding(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 3:
            await update.effective_message.reply_text("Usage: /set AAPL 10 185.50")
            return
        try:
            ticker = normalize_ticker(context.args[0])
            quantity = self._positive_decimal(context.args[1], "Shares")
            average_cost = self._positive_decimal(context.args[2], "Average cost", allow_zero=True)
            holding = self.database.set_holding(user_id, ticker, quantity, average_cost)
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(
            f"Replaced {ticker}: {format(holding.quantity.normalize(), 'f')} shares at "
            f"{money(average_cost)} average cost."
        )

    async def remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 1:
            await update.effective_message.reply_text("Usage: /remove AAPL")
            return
        try:
            ticker = normalize_ticker(context.args[0])
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        removed = self.database.remove_holding(user_id, ticker)
        await update.effective_message.reply_text(
            f"Removed {ticker}." if removed else f"{ticker} was not in your portfolio."
        )

    async def cash(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 1:
            await update.effective_message.reply_text("Usage: /cash 1000")
            return
        try:
            amount = self._positive_decimal(context.args[0], "Cash", allow_zero=True)
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        self.database.set_cash(user_id, amount)
        await update.effective_message.reply_text(f"Tracked portfolio cash set to {money(amount)}.")

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(await self.service.portfolio_text(user_id))

    async def risk(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(await self.service.risk_text(user_id))

    async def brief(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(await self.service.daily_brief_text(user_id))

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._authorize(update) is None:
            return
        if len(context.args) != 1:
            await update.effective_message.reply_text("Usage: /analyze NVDA")
            return
        try:
            ticker = normalize_ticker(context.args[0])
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(await self.service.security_text(ticker))

    async def watch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 1:
            await update.effective_message.reply_text("Usage: /watch NVDA")
            return
        try:
            ticker = normalize_ticker(context.args[0])
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        self.database.add_watch(user_id, ticker)
        await update.effective_message.reply_text(f"Added {ticker} to your watchlist.")

    async def unwatch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if len(context.args) != 1:
            await update.effective_message.reply_text("Usage: /unwatch NVDA")
            return
        try:
            ticker = normalize_ticker(context.args[0])
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        removed = self.database.remove_watch(user_id, ticker)
        await update.effective_message.reply_text(
            f"Removed {ticker} from your watchlist."
            if removed
            else f"{ticker} was not on your watchlist."
        )

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(await self.service.watchlist_text(user_id))

    async def tip(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(await self.service.tip_text(user_id))

    async def daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if not context.args:
            user = self.database.get_user(user_id)
            state = "enabled" if user and user.daily_brief_enabled else "paused"
            await update.effective_message.reply_text(
                f"Daily brief is {state}. Schedule: {user.daily_brief_time} {user.timezone}"
                if user
                else "No schedule found."
            )
            return
        if context.args[0].lower() == "off":
            self.database.set_daily_enabled(user_id, False)
            self._remove_user_jobs(context.application, user_id)
            await update.effective_message.reply_text("Automatic daily briefs are paused.")
            return
        daily_time = context.args[0]
        timezone_name = (
            context.args[1] if len(context.args) >= 2 else self.settings.default_timezone
        )
        try:
            parse_clock(daily_time, timezone_name)
            ZoneInfo(timezone_name)
        except (ConfigurationError, ZoneInfoNotFoundError) as exc:
            await update.effective_message.reply_text(str(exc))
            return
        self.database.set_daily_schedule(user_id, daily_time, timezone_name, enabled=True)
        user = self.database.get_user(user_id)
        self._schedule_user(context.application, user)
        await update.effective_message.reply_text(
            f"Daily brief scheduled for {daily_time} in {timezone_name}."
        )

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        user = self.database.get_user(user_id)
        if user is None:
            return
        enabled = "on" if user.daily_brief_enabled else "off"
        provider = self.settings.market_data_provider
        await update.effective_message.reply_text(
            f"Daily brief: {enabled}\n"
            f"Time: {user.daily_brief_time}\n"
            f"Timezone: {user.timezone}\n"
            f"Market adapter: {provider}\n"
            "Trading: disabled"
        )

    async def show_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is not None:
            await update.effective_message.reply_text(
                f"Your Telegram user ID is {user_id}. Keep IDs in the private beta allowlist."
            )

    async def privacy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._authorize(update) is None:
            return
        await update.effective_message.reply_text(
            "🔐 PRIVACY AND SAFETY\n\n"
            "This MVP stores your Telegram numeric user ID, chat ID, manually entered holdings, "
            "watchlist, cash amount, timezone, and notification schedule in its local database.\n\n"
            "It does not request brokerage credentials and cannot place orders. "
            "Do not send account numbers, passwords, tax IDs, or other secrets.\n\n"
            "Use /delete_me CONFIRM to remove your stored bot data."
        )

    async def delete_me(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self._authorize(update)
        if user_id is None:
            return
        if context.args != ["CONFIRM"]:
            await update.effective_message.reply_text(
                "This permanently deletes your bot portfolio, watchlist, cash, and schedule. "
                "Run /delete_me CONFIRM to continue."
            )
            return
        self._remove_user_jobs(context.application, user_id)
        self.database.delete_user(user_id)
        await update.effective_message.reply_text("Your stored bot data has been deleted.")

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self._authorize(update) is not None:
            await update.effective_message.reply_text("Unknown command. Use /help.")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.exception("Unhandled Telegram update error", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Something went wrong. No order was placed. Please try again later."
            )

    async def daily_job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        if context.job is None:
            return
        user_id = int(context.job.data)
        user = self.database.get_user(user_id)
        if user is None or not user.daily_brief_enabled:
            return
        text = await self.service.daily_brief_text(user_id)
        await context.bot.send_message(chat_id=user.chat_id, text=text)

    def _schedule_user(self, application: Application, user: UserRecord | None) -> None:
        if user is None or not user.daily_brief_enabled or application.job_queue is None:
            return
        self._remove_user_jobs(application, user.telegram_user_id)
        application.job_queue.run_daily(
            self.daily_job,
            time=parse_clock(user.daily_brief_time, user.timezone),
            data=user.telegram_user_id,
            chat_id=user.chat_id,
            user_id=user.telegram_user_id,
            name=f"daily-brief-{user.telegram_user_id}",
        )

    @staticmethod
    def _remove_user_jobs(application: Application, user_id: int) -> None:
        if application.job_queue is None:
            return
        for job in application.job_queue.get_jobs_by_name(f"daily-brief-{user_id}"):
            job.schedule_removal()

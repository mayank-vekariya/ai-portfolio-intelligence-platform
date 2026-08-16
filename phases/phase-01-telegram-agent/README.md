# Phase 1 — Telegram Portfolio Agent

This folder is the first working phase of the
[AI Portfolio Intelligence Platform](../../README.md). The complete product strategy,
architecture, security model, brokerage roadmap, AI workflow, and delivery milestones are in
[`planning/PROJECT_PLAN.md`](../../planning/PROJECT_PLAN.md).

It is a Telegram-only private beta for manually tracking a stock
portfolio, receiving a daily summary, reviewing concentration and material moves, and inspecting
technical context for a ticker. Telegram is the validation wedge, not the final product boundary;
the roadmap expands into licensed market intelligence, connected portfolios, a responsive web
application, and—only after regulatory review—carefully bounded advice or execution workflows.

The bot cannot connect to a brokerage or place an order. It uses neutral review language rather than personalized buy/sell instructions.

## What works

- Private-chat-only Telegram commands.
- Optional allowlist for five beta users.
- Manual holdings, weighted average cost, tracked cash, and watchlist.
- Current portfolio value, daily move, gain/loss, and position weights.
- Concentration, large-move, drawdown-from-cost, and incomplete-data alerts.
- On-demand ticker analysis with trend, momentum, volatility, drawdown, and RSI context.
- Scheduled per-user daily briefs with IANA timezones.
- SQLite tenant isolation keyed by the authenticated Telegram user ID.
- User-controlled data deletion.
- Deterministic offline demo and test fixtures.
- Docker deployment using long polling.

## Important prototype limitation

The default `yahoo` adapter calls an unofficial public chart endpoint and is included only to make a private technical prototype useful. Its availability, accuracy, delay, terms, and redistribution rights are not guaranteed.

Before inviting public or paying users, implement a licensed commercial `MarketDataProvider`, preserve provider timestamps and entitlements, and remove the prototype adapter from production.

## Run the offline demo

The demo does not need Telegram or network access.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
portfolio-bot-demo
```

## Create and run the Telegram bot

1. Open Telegram and message the official `@BotFather` account.
2. Run `/newbot`, choose a name and a username ending in `bot`, and copy the token.
3. Copy `.env.example` to `.env`.
4. Put the token in `TELEGRAM_BOT_TOKEN`.
5. For a private beta, add comma-separated numeric Telegram user IDs to `ALLOWED_TELEGRAM_USER_IDS`.
6. Run:

```powershell
.\.venv\Scripts\Activate.ps1
portfolio-telegram-bot
```

The token is an account credential. Never paste it into source code, commit it, include it in a screenshot, or send it in a Telegram chat.

## First Telegram session

```text
/start
/id
/add AAPL 10 185.50
/add MSFT 4 410
/cash 2000
/watch NVDA
/portfolio
/risk
/brief
/analyze NVDA
/daily 07:30 America/Los_Angeles
```

`/add` combines a new lot with an existing holding using a weighted average. Use `/set` to replace the entire tracked position.

## Docker

After creating `.env`:

```powershell
docker compose up --build -d
docker compose logs -f portfolio-bot
```

The SQLite database is stored in the local `data` directory. Back it up before upgrading or moving the service.

## Tests and quality checks

```powershell
pytest
ruff check .
```

## Security behavior

- The bot refuses portfolio operations in groups.
- The optional user allowlist limits the private beta.
- Tenant authority comes from Telegram's authenticated `effective_user.id`, never message text.
- Monetary values use `Decimal` and are stored as decimal strings.
- The bot does not accept account credentials or account numbers.
- `/delete_me CONFIRM` removes the user's stored portfolio data.
- No order-placement code exists.

## Deployment choice

This MVP uses Telegram long polling because it is the smallest reliable deployment for five users. Run one bot process in Docker on an always-on host. Do not run multiple polling replicas for the same token.

For a later AWS production version, move to Telegram webhooks with API Gateway/Lambda, use Telegram's webhook secret header, replace SQLite with PostgreSQL or DynamoDB, and trigger daily briefs through EventBridge Scheduler.

## Next milestone

1. Test the bot for one market week with manual portfolios.
2. Measure whether users open and act on the brief.
3. Add a licensed data adapter and SEC filing/event ingestion.
4. Add a structured investment-policy questionnaire.
5. Add evidence links and material-change suppression.
6. Complete legal review before charging for personalized securities recommendations.

Official references:

- [Telegram Bot tutorial](https://core.telegram.org/bots/tutorial)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot](https://python-telegram-bot.org/)

For host-by-host instructions, backups, upgrades, and production gates, see the
[repository deployment guide](../../DEPLOYMENT.md).

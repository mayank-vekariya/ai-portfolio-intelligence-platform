# Deployment Guide

This repository has two different deployments:

1. The public project showcase is a static GitHub Pages site from `docs/` on `main`.
2. The Telegram agent is a long-running private service from `phases/phase-01-telegram-agent/`.

## Public project showcase

The site uses plain HTML, CSS, and JavaScript, so it needs no build step. GitHub Pages publishes
the `/docs` folder from the `main` branch.

To preview locally from the repository root:

```powershell
python -m http.server 4173 --directory docs
```

Open `http://localhost:4173`. Changes pushed to `main/docs` are published by GitHub Pages.

## Telegram agent prerequisites

- Python 3.11 or newer, or Docker Desktop.
- A bot created through Telegram's official `@BotFather` account.
- The numeric Telegram user IDs allowed to use the private beta.
- An always-on host with persistent storage.

Never commit `.env`, the bot token, user IDs, or a live SQLite database.

## Local Python deployment

```powershell
Set-Location .\phases\phase-01-telegram-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill in `.env`, then verify before running:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\portfolio-bot-demo.exe
.\.venv\Scripts\portfolio-telegram-bot.exe
```

The final command stays running and receives Telegram updates through long polling.

## Docker deployment

From `phases/phase-01-telegram-agent`:

```powershell
Copy-Item .env.example .env
# Fill in .env before continuing.
docker compose up --build -d
docker compose logs -f portfolio-bot
```

The compose file mounts `./data` into the container. Back up `data/portfolio_bot.sqlite3` before
an upgrade or host migration. Run only one polling process for a bot token.

To update:

```powershell
git pull --ff-only
docker compose up --build -d
```

## Always-on host choices

For the five-user pilot, one small Linux virtual machine or container host is enough. Copy only
the Phase 1 folder, create `.env` on the host, and keep the `data` volume persistent. Configure
host-level restart and monitoring in addition to Docker's `restart: unless-stopped` policy.

For a later AWS production version, replace long polling with a verified Telegram webhook,
API Gateway/Lambda, EventBridge scheduling, and a managed multi-user database. Do not add that
complexity before the pilot validates demand.

## Deployment checklist

- [ ] Token was created by the owner and stored only in `.env` or a secret manager.
- [ ] `ALLOWED_TELEGRAM_USER_IDS` contains only invited users.
- [ ] Tests and lint pass.
- [ ] One bot process is running.
- [ ] The SQLite path uses persistent storage.
- [ ] A backup and restore test has been completed.
- [ ] Logs contain no token, account number, or portfolio export.
- [ ] `/delete_me CONFIRM` was tested with non-production data.

## Production gates

The prototype Yahoo adapter is not a licensed production data feed. Before a public or paid
launch, replace it with a commercially licensed provider, show source timestamps, complete
security review, and obtain U.S. securities-law advice appropriate to the final product behavior.

# AI Portfolio Intelligence Platform

[![CI](https://github.com/mayank-vekariya/ai-portfolio-intelligence-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/mayank-vekariya/ai-portfolio-intelligence-platform/actions/workflows/ci.yml)
[![Project site](https://img.shields.io/badge/project_site-live-b8ff70?labelColor=101813)](https://mayank-vekariya.github.io/ai-portfolio-intelligence-platform/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-d6e8ff?labelColor=101813)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-f4d38a?labelColor=101813)](LICENSE)

[![AI Portfolio Intelligence project preview](docs/assets/og-card.png)](https://mayank-vekariya.github.io/ai-portfolio-intelligence-platform/)

An evidence-backed, cross-broker portfolio intelligence project built in deliberate phases.
The first working phase is a private Telegram agent that tracks a manually entered portfolio,
produces daily briefs, highlights risk, and explains technical context without placing trades.

**[View the project showcase](https://mayank-vekariya.github.io/ai-portfolio-intelligence-platform/)** ·
**[Run the Telegram phase](phases/phase-01-telegram-agent/README.md)** ·
**[Read the master plan](planning/PROJECT_PLAN.md)**

> This is an educational decision-support prototype, not an investment adviser or brokerage.
> No code in Phase 1 can place an order.

## Project phases

| Phase | Folder | Status | Outcome |
| --- | --- | --- | --- |
| 1 | [`phase-01-telegram-agent`](phases/phase-01-telegram-agent/) | Working MVP | Private Telegram briefs, portfolio summaries, risk review, and ticker analysis |
| 2 | [`phase-02-web-application`](phases/phase-02-web-application/) | Planned | Responsive portfolio dashboard and evidence-backed decision cards |
| 3 | [`phase-03-connected-portfolios`](phases/phase-03-connected-portfolios/) | Planned | Approved read-only brokerage connections and multi-account views |
| 4 | [`phase-04-financial-planning`](phases/phase-04-financial-planning/) | Future | Income, expenses, emergency savings, retirement, and goal-based planning |

The current build stays intentionally narrow. It proves that a small group of users repeatedly
values a daily brief and risk-first alerts before the project invests in broker connections,
licensed market data, AWS infrastructure, or a full application.

## What Phase 1 already does

- Keeps each Telegram user's portfolio isolated by authenticated Telegram user ID.
- Tracks holdings, weighted average cost, cash, and a watchlist.
- Calculates portfolio value, gain/loss, daily movement, concentration, and drawdown alerts.
- Produces scheduled daily briefs in each user's timezone.
- Explains trend, momentum, volatility, drawdown, and RSI for a requested ticker.
- Offers an offline deterministic demo and an automated test suite.
- Runs locally or in Docker using Telegram long polling.
- Supports complete user-data deletion with `/delete_me CONFIRM`.

## Quick demonstration

```powershell
Set-Location .\phases\phase-01-telegram-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\portfolio-bot-demo.exe
```

The demo is offline: it uses deterministic fixture prices and does not require a Telegram token,
brokerage login, or network connection.

## Repository map

```text
phases/                  Independently documented product phases
  phase-01-telegram-agent/  Working Python Telegram MVP and tests
  phase-02-web-application/ Future responsive application boundary
  phase-03-connected-portfolios/ Read-only integration boundary
  phase-04-financial-planning/ Long-term financial-planning boundary
planning/                Product strategy and coding-agent brief
docs/                    Public GitHub Pages showcase
.github/workflows/       Credential-free CI
ROADMAP.md               Delivery status and next gates
DEPLOYMENT.md            Website and bot deployment guide
```

## Product principle

Research the market once, then perform lightweight deterministic checks for each affected
portfolio. An explanatory model may summarize verified evidence, but it never performs
authoritative portfolio math and never receives a trading tool.

## Documentation

- [Current roadmap and progress](ROADMAP.md)
- [Deployment guide](DEPLOYMENT.md)
- [Master product and architecture plan](planning/PROJECT_PLAN.md)
- [Coding-agent handoff brief](planning/CODING_AGENT_BRIEF.md)
- [Security policy](SECURITY.md)
- [Contribution guide](CONTRIBUTING.md)

## License

Released under the [MIT License](LICENSE).

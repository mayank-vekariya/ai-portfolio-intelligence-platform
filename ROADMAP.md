# Product Roadmap and Status

Last updated: August 15, 2026

## Current status

Phase 1 is implemented as a Telegram-only MVP. The project has a public showcase, offline demo,
Docker packaging, user-isolated SQLite storage, and automated tests. Live Telegram operation
requires the owner to create a BotFather token and configure the intended beta-user IDs.

| Workstream | State | Evidence / next gate |
| --- | --- | --- |
| Product thesis and competitor research | Complete | `planning/PROJECT_PLAN.md` |
| Phase-based repository structure | Complete | `phases/` |
| Telegram commands and scheduled briefs | Complete | `phases/phase-01-telegram-agent/src/` |
| Offline deterministic demo | Complete | Run `portfolio-bot-demo` |
| Automated quality checks | Complete | CI plus 12 local tests |
| Public project explanation | Complete | GitHub Pages from `docs/` |
| Live private Telegram pilot | Owner setup needed | BotFather token and allowlisted user IDs |
| Licensed production market data | Not started | Provider and commercial-license decision |
| Shared research pipeline | Not started | Phase 1 engagement gate |
| Responsive web application | Planned | Phase 2 |
| Read-only broker connections | Planned | Phase 3 |
| Full financial planning | Future | Phase 4 |
| Live trading | Explicitly excluded | Legal, regulatory, security, and product gates |

## The next practical milestone

Run Phase 1 with up to five invited users for one market week. Track:

1. How many daily briefs are opened.
2. Which risk alerts lead to a deeper `/analyze` request.
3. Which explanations users find unclear or untrustworthy.
4. Whether users return without being prompted.
5. Which missing feature blocks continued use.

Only after that pilot should the project purchase licensed data or build the web application.

## Definition of success for Phase 1

- A new user can add a portfolio without help.
- Scheduled briefs arrive at the expected local time.
- Every metric shown by the bot is reproducible in tests.
- One user cannot read or modify another user's data.
- Users understand that alerts are review prompts, not guaranteed predictions.
- The team can identify one repeated, high-value workflow to carry into Phase 2.

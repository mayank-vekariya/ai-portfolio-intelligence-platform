# Coding Agent Brief - Start Here

> Status update: this original web-first brief is retained for the later web milestone. The
> active implementation is now the Telegram-only pilot documented in
> [`phases/phase-01-telegram-agent`](../phases/phase-01-telegram-agent/).

Use [`PROJECT_PLAN.md`](PROJECT_PLAN.md) as the product source of truth.

## Your role

Act as the staff full-stack engineer for the AI Portfolio Intelligence project. Build a secure, testable foundation for a five-user private beta.

## Scope for this assignment

Complete only Milestone 0 and Milestone 1 from `PROJECT_PLAN.md`.

Do not integrate live market data, Bedrock, Robinhood, SnapTrade, Plaid, Telegram, or live trading in this assignment. Define clean interfaces for later providers, but use deterministic fixtures now.

## Required output

### 1. Planning artifacts

Create:

- `docs/adr/0001-system-architecture.md`
- `docs/threat-model.md`
- `docs/data-model.md`
- `docs/api/openapi.yaml`
- `docs/schemas/decision-card.schema.json`
- `docs/import-format.md`
- `docs/wireframes.md`
- An implementation backlog with small, testable tasks.

Document assumptions. If an assumption is reversible, choose a sensible default and continue. Stop only for a decision that would materially change security, product scope, or data ownership.

### 2. Repository foundation

Create this monorepo:

```text
apps/web        Next.js + TypeScript
apps/api        Python FastAPI
apps/worker     Python job package
packages/schemas
packages/ui
packages/provider-fixtures
infra/cdk       AWS CDK in TypeScript
```

Provide one-command local setup using documented package scripts and Docker Compose for PostgreSQL. Pin important tool versions and include `.env.example` files containing placeholders only.

### 3. Features

Implement:

- Local authentication suitable for development plus a production Cognito adapter/interface.
- Five seeded test users.
- Strict server-side tenant isolation.
- Manual portfolio creation.
- Manual cash and holding entry.
- CSV upload using the canonical template.
- Import preview and validation report.
- Portfolio dashboard with fixture prices.
- Holdings table.
- Allocation and sector exposure.
- Daily/total gain and loss.
- Position concentration.
- Historical volatility and maximum drawdown from fixture history.
- Upcoming fixture events.
- Responsive layout.

### 4. Provider contracts

Define interfaces for:

- Market data.
- Fundamentals.
- News.
- SEC filings.
- Macro data.
- Brokerage data.
- LLM/explanation provider.

Implement fixture-backed adapters only.

### 5. Tests

At minimum, add:

- Unit tests for every portfolio calculation.
- CSV parsing, ambiguous ticker, duplicate row, negative quantity, missing cost basis, split-adjustment, and formula-injection tests.
- API authorization tests proving one user cannot access another user's data.
- Provider contract tests against fixtures.
- Database migration tests.
- A smoke test for the main dashboard flow.

Never rely on a live third-party service in the test suite.

## Engineering rules

- All money uses decimal-safe types; never binary floating point for authoritative monetary values.
- Store timestamps in UTC and render them in the user's timezone.
- Version portfolio imports and investment policies.
- Do not accept `user_id` as authority from the browser; derive identity from authentication.
- All user-owned database rows contain `user_id`.
- Validate input at API and domain boundaries.
- Escape spreadsheet formulas when generating CSV.
- Keep raw provider payloads out of domain models.
- Use database migrations; do not create production schemas ad hoc.
- Include structured logs and request/job correlation IDs.
- No LLM may perform portfolio math.
- No order-placement interface is enabled in the running application.
- Preserve a clean separation between shared market data and user-owned portfolio data.

## Definition of done

The assignment is complete when:

1. A new developer can follow the README and start the system locally.
2. Five seeded users can sign in independently.
3. Each user can import a fixture CSV and see correct portfolio analytics.
4. Cross-user access attempts fail in automated tests.
5. Calculations reconcile to documented fixture answers.
6. The dashboard works at desktop and mobile widths.
7. CI runs formatting, linting, type checking, migrations, unit tests, API integration tests, and the smoke test.
8. No feature uses live data or can place an order.

At the end, report:

- What was built.
- Exact commands to run it.
- Tests run and results.
- Known limitations.
- Decisions that need human approval before Milestone 2.

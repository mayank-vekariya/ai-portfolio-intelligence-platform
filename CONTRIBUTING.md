# Contributing

Thanks for helping improve the AI Portfolio Intelligence Platform.

## Before opening a change

- Keep work inside the relevant `phases/phase-*` folder.
- Do not add live trading, brokerage credentials, personal portfolio data, or scraped paid data.
- Update `ROADMAP.md` when a milestone or product boundary changes.
- Keep deterministic calculations separate from generated explanations.
- Add or update tests for every calculation, authorization rule, and data transformation.

## Phase 1 checks

```powershell
Set-Location .\phases\phase-01-telegram-agent
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Open a focused pull request explaining what changed, why, the user impact, and the checks run.

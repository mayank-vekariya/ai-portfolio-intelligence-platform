# Security Policy

## Supported version

Only the latest commit on `main` is supported during the prototype stage.

## Reporting a vulnerability

Do not open a public issue containing a bot token, user ID, portfolio data, provider credential,
or exploit instructions. Use GitHub's private vulnerability reporting feature when enabled, or
contact the repository owner privately through their GitHub profile.

## Sensitive data rules

- Never commit `.env`, databases, logs, account numbers, tokens, or portfolio exports.
- Derive tenant identity from Telegram's authenticated user object, never message text.
- Use an explicit Telegram user allowlist for the private pilot.
- Treat prices and external text as untrusted, timestamped input.
- Do not give a language model or Telegram handler an order-placement tool.
- Replace the prototype market-data adapter before public or paid use.

If a secret is exposed, revoke and rotate it immediately, then remove the affected data from the
repository history before continuing deployment.

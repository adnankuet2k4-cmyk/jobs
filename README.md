# Alert monitor

Watches RSS/Atom feeds for job postings, company news, and brand/lead mentions;
sends new matches to Slack and/or Telegram. Runs daily via GitHub Actions.

## Step 1 – Define what to monitor
Edit `config.json`. Each watch has a `name`, feed `url`, and optional
`include` / `exclude` keyword lists (case-insensitive, matched on title + summary).

Feed sources that work without scraping LinkedIn:
- **Google Alerts** (deliver to "RSS feed") for `site:linkedin.com/jobs "title"`, company names, or brand mentions
- Company blog / newsroom / careers RSS
- Job-board RSS (Indeed, RemoteOK, We Work Remotely, etc.)

> LinkedIn's official API is restricted to approved partners and its ToS forbids
> scraping, so this tool deliberately consumes feeds rather than LinkedIn directly.

## Step 2 – Notifications
Set repo secrets: `SLACK_WEBHOOK_URL` and/or `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
With none set, matches print to stdout.

## Run locally
    python3 monitor.py

The first run records existing items without alerting; later runs alert only on new ones.
State lives in `seen.json` (committed by the workflow).

## No-code alternative
Make.com / Zapier / Relay: RSS trigger → filter step → Slack/Telegram/Email action,
scheduled daily. Same feeds and keywords as above.

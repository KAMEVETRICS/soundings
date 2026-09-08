# Soundings — Project Submission

Copy these answers into the official Project Submission Form.

## Project

- **Name:** Soundings
- **Tagline:** What the crowd feels versus how the tape is positioned.
- **Tracks entered:** Track 2 Dashboards & Interfaces (data analytics)
- **One-line user:** A trader who wants a 30-second read of Fear & Greed against BTC funding, liquidations, breadth and dominance — without a fake order book.
- **Decision improved:** Is surface greed confirmed by positioning, or is the crowd hotter than the tape?

## What it does

Soundings is a read-only market terminal on RYO’s six research tools.

- **Overview** — regime, 24h volume, market cap, breadth, volume vs cap.
- **Analytics** — positioning-stress **S** (0.5 Fear & Greed + 0.5 BTC funding percentile). Gap label. Component table. Optional TrueNorth F&G / MVRV as a second book.
- **Screener** — `scan_market` ranked by 24h move, turnover, spike flags.
- **Token** — `analyze_token` + `deep_analysis` in parallel: horizons, RSI, ATR, confluence gates.
- **Sentiment** — 7-day F&G, BTC funding crowding, liquidations, altseason.
- **Compare** — `compare_tokens` factor scores.
- **Claw** — answers only from the live evidence pack.

Missing fields stay blank. Last-good RYO cache is labelled stale. Open interest is not on this book.

## How it uses RYO

| Tool | Where |
| --- | --- |
| `market_overview` | Overview, Analytics, Sentiment, Insights |
| `monitor_market_sentiment_shift` | Funding, liquidations, altseason, S |
| `scan_market` | Overview chart, Screener |
| `analyze_token` | Token page, BTC stretch readout |
| `deep_analysis` | Token confluence / ATR plan |
| `compare_tokens` | Compare |

Soundings does not send orders. Optional TrueNorth is F&G / MVRV only.

## Demo script (for the video)

1. Open `/analytics`. Read **S**, the **gap** label, and the component table in 30 seconds.
2. `/` — regime, breadth, volume vs market cap.
3. `/screener` — open a name.
4. `/token/SOL` — RSI, gates, ATR plan.
5. `/sentiment` — F&G vs funding crowding vs liquidation side.
6. `/compare?symbols=SOL,ETH,BTC`.
7. `/api/overview` and `/api/analytics` — same desks as JSON.
8. `/claw` — “Is the crowd hotter than BTC funding?”

## Environment

See `.env.example`. Never commit a live key.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/analytics

## Repo

https://github.com/KAMEVETRICS/soundings

## Team

Fill Discord IDs and GitHub usernames from the organiser DM.

## Social post (optional award)

Draft: screenshot of Analytics (S + gap). Tag @ryodigital. “Soundings reads Fear & Greed against BTC funding from live RYO tools — crowd vs tape, no invented OI.” Link the repo.

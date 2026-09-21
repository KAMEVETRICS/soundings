# Soundings

Read-only market terminal on RYO's six research tools.

**RYO-CHAN Hackathon 2026 · Track 2 Dashboards & Interfaces.**

The Analytics desk answers one question: is Fear & Greed confirmed by BTC funding, or is the crowd hotter than the tape? Positioning-stress **S** is `0.5` Fear & Greed + `0.5` BTC funding percentile on this live snapshot. Missing fields stay blank. RYO does not publish wallets or open interest, so those prints are not shown.

| Page | What it is | Source |
| --- | --- | --- |
| Overview | 30-second regime, Fear & Greed, breadth, volume vs cap | `market_overview` + `scan_market` + sentiment |
| **Analytics** | Crowd vs tape: positioning-stress **S**, gap, components | sentiment funding/liq + F&G + BTC RSI readout |
| Screener | Ranked candidates, turnover, spike flags | `scan_market` |
| Token | Horizons, RSI, ATR, gates, ATR preview plan | `analyze_token` + `deep_analysis` |
| Sentiment | Seven-day F&G, BTC funding, liquidations, altseason | `monitor_market_sentiment_shift` |
| Compare | Momentum / activity / volatility factors | `compare_tokens` |
| Insights | Derived cards from the same snapshot | no extra tools |
| Claw | Ask what changed; answers only from live evidence | overview + sentiment + optional token + OpenRouter |

JSON for every desk lives under `/api`. OpenAPI explorer: `/docs`.

No fabricated prints. Last-good cache is labelled stale. Open interest is unavailable on this book; we do not invent it.

Live: https://soundings.online/analytics

## Stack

Python 3.12, FastAPI, uvicorn, httpx, Jinja2, python-dotenv, openai (OpenRouter for Claw), pytest. Optional TrueNorth MCP for a second Fear & Greed / MVRV book.

## Run

Copy `.env.example` to `.env` and fill `RYO_MCP_KEY`. Optional: `OPENROUTER_API_KEY`, `TRUENORTH_MCP_TOKEN`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Data endpoints

Slices of overview (totals, funding, gates, …) live **on the pack**, not as extra routes. OpenAPI: `/docs`.

| Method | Path | What you get |
| --- | --- | --- |
| GET | `/api` | Catalog |
| GET | `/api/health` | Process + key flags |
| GET | `/api/catalog` | Live RYO `/tools` list |
| GET | `/api/whoami` | RYO identity, secrets stripped |
| GET | `/api/overview` | Regime, totals, movers, stress, insights |
| GET | `/api/analytics` | Crowd vs tape (S, gap, BTC RSI, optional TrueNorth F&G/MVRV) |
| GET | `/api/screener?top_n=` | Ranked scan (1–16) |
| GET | `/api/token/{symbol}` | Fast read + deep pack |
| GET | `/api/compare?symbols=` | Factor comparison |
| POST | `/api/claw` | `{ "question": "..." }` |

## How S is built

Weights: `0.5` Fear & Greed + `0.5` funding. Stretch is shown at weight `0`.

- Crowd: live map `(Fear & Greed - 50) / 25`
- Tape: RYO's 90-day percentile of BTC 7-day funding, mapped the same way
- Stretch: BTC RSI(14), not inside S
- Liquidations, dominance, and breadth sit beside S
- Live snapshot, not a rolling z-score, not a trade, not open interest

## Demo script

1. Analytics — read S, the gap label, and the component table in 30 seconds.
2. Overview — regime, breadth, volume vs market cap (not OI).
3. Screener — sort is already by 24h magnitude; open a name.
4. Token — RSI, gates, ATR preview plan marked preview_only.
5. Sentiment — F&G vs funding crowding vs liquidation side.
6. Compare — `SOL, ETH, BTC`.
7. `/api/analytics` — same desk as JSON.
8. Claw — "Is the crowd hotter than BTC funding?"

## How it works

1. FastAPI calls RYO MCP REST (`/tools`, then the six research tools) with `RYO_MCP_KEY`.
2. Successful payloads sit in a memory + disk TTL cache (`RYO_CACHE_TTL`, default 180s; last-good served up to `RYO_SWR_TTL`). Failures keep last-good data and mark it stale. Missing fields stay blank. Sidebar swaps the main pane so the chrome stays put.
3. One market pack (`_fetch_market` → `_assemble_market`) feeds Overview, Analytics, Sentiment, and Insights. Token pages gather `analyze_token` + `deep_analysis`. Compare is `compare_tokens`.
4. Analytics derives **S** and the gap label from that pack. Optional TrueNorth Fear & Greed / MVRV is a second book, not a substitute for RYO.
5. Claw may call OpenRouter/xAI and is only allowed to talk about the live evidence pack.

## Submission

**Track 2 (Dashboards & Interfaces).** Form: `RYOCHAN-Project-Submission-Form.pdf`.

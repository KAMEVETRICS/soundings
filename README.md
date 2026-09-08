# Soundings

A hydrographic survey of live crypto markets.

Built for **RYO-CHAN Hackathon 2026 · Track 2 Dashboards & Interfaces** (data analytics). Inspired by the Datatides terminal layout and by [Undertow’s analytics desk](https://under-tow.vercel.app/analytics): **what the crowd feels versus how the tape is positioned**.

Datatides watches Pacifica perps and wallets. Undertow backtests a rolling z-score of Fear & Greed vs funding. Soundings cannot copy either pipe: RYO tools do not accept wallet addresses, do not publish a 90-day OI history, and cannot trade. We survey **live measurements** from RYO’s six research tools, then derive the gap. Missing fields stay blank.

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

No fabricated prints. Last-good cache is labelled stale. Open interest is **unavailable** on this book — we do not invent it.

## Run

Uses the parent folder `.env` (same RYO / OpenRouter / TrueNorth keys as Chamber).

```powershell
cd "build 2"
python -m uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/analytics

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

Undertow’s frozen weights are `0.5` Fear & Greed + `0.5` funding, stretch `0`. Soundings uses the same weights on **this snapshot**:

- Crowd: live map `(Fear & Greed − 50) / 25`
- Tape: RYO’s own 90-day percentile of BTC 7-day funding, mapped the same way
- Stretch: BTC RSI(14) is shown, weight 0
- Liquidations / dominance / breadth sit beside S, not inside it
- **Not** a rolling z-score, **not** a trade, **not** open interest

## Demo script

1. Analytics — read S, the gap label, and the component table in 30 seconds.
2. Overview — regime, breadth, volume vs market cap (not OI).
3. Screener — sort is already by 24h magnitude; open a name.
4. Token — RSI, gates, ATR preview plan marked preview_only.
5. Sentiment — F&G vs funding crowding vs liquidation side.
6. Compare — `SOL, ETH, BTC`.
7. `/api/analytics` — same desk as JSON.
8. Claw — "Is the crowd hotter than BTC funding?"

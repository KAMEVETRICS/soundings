# Soundings — Project Submission

**Track: Track 2 Dashboards & Interfaces (data analytics).** Not Track 1. Not Track 3.

Organizer private repo (this is what `/apply` wants):

- URL: https://github.com/RYO-Digital/ryochan-hackathon_repository-142
- **Repository name for Discord `/apply`:** `ryochan-hackathon_repository-142`

Public showcase: https://github.com/KAMEVETRICS/soundings

The organizer repo is private, empty, and this GitHub account can push to `main`. Nothing has been pushed (per “do not push”).

---

## Still yours

1. **Demo video.** Record the script below. Upload to Google Drive / Dropbox / OneDrive. Share so organizers can open it. If the file is locked, put the password next to the link. Then set `DEMO_VIDEO` in `scripts/fill_submission_form.py` and rebuild the PDF.
2. **Discord `/apply`:**
   - Go to `#buidl` (`1538785340880461905`)
   - Type `/apply` → **Hackathon Submission**
   - Paste exactly: `ryochan-hackathon_repository-142`
   - Wait for results in `1535192398437818388`

---

## Form answers (on the PDF)

| Field | Value |
| --- | --- |
| Total Members | 1 |
| Name | kongclaves |
| Role | Solo builder |
| Email | kcfreshkl@gmail.com |
| Project | Soundings |
| Track | Track 2 (Dashboards & Interfaces) |
| Problem | Fear & Greed can disagree with BTC funding. RYO does not publish wallets or open interest, so those prints cannot be shown. |
| Solution | Read-only terminal on RYO's six research tools. Analytics reports crowd vs tape as S = 0.5 Fear & Greed + 0.5 BTC funding percentile. Missing fields stay blank. |
| Key Features | Overview, Analytics (S and gap), Screener, Token, Sentiment, Compare, Claw, JSON /api. |
| Target Users | Traders who want a 30-second crowd-vs-tape read. |
| Scope | Live RYO MCP six tools. Optional TrueNorth F&G / MVRV. No orders. |
| Limitations | No wallet lookup, no open interest. |
| Frontend | Jinja2, CSS, vanilla JS |
| Backend | Python 3.12, FastAPI, uvicorn, httpx |
| AI Model(s) | None on market desks. Claw optional: OpenRouter x-ai/grok-4.3 |
| Other | python-dotenv; optional TrueNorth MCP |
| Github Repository | https://github.com/RYO-Digital/ryochan-hackathon_repository-142 |
| Demo Video | *(blank until you set DEMO_VIDEO)* |
| Documentation | README.md |
| How to run | https://soundings.online/analytics |
| Prerequisites | Python 3.12, pip, RYO_MCP_KEY |
| Installation | Clone; venv; pip install -r requirements.txt; copy .env.example to .env |
| Environment Variables | RYO_MCP_URL, RYO_MCP_KEY. Optional: OPENROUTER_API_KEY, TRUENORTH_MCP_URL, TRUENORTH_MCP_TOKEN |
| Build Command | None |
| Run Command | `uvicorn app.main:app --host 127.0.0.1 --port 8001` |
| Test Command | `python scripts/probe_endpoints.py` |
| Test Account(s) | None |

### Environment

See `.env.example`. Never commit a live key.

```
RYO_MCP_URL=https://app-ryochan.com/api/mcp
RYO_MCP_KEY=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
CHAMBER_MODEL=x-ai/grok-4.3
TRUENORTH_MCP_URL=https://mcp.true-north.xyz/mcp
TRUENORTH_MCP_TOKEN=
RYO_CACHE_TTL=180
```

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload --reload-dir app
```

Open http://127.0.0.1:8001/analytics

---

## How it uses RYO

| Tool | Where |
| --- | --- |
| `market_overview` | Overview, Analytics, Sentiment, Insights |
| `monitor_market_sentiment_shift` | Funding, liquidations, altseason, S |
| `scan_market` | Overview chart, Screener |
| `analyze_token` | Token page, BTC stretch readout |
| `deep_analysis` | Token confluence / ATR plan |

Soundings does not send orders.

---

## Demo script (for the video)

1. Open `/analytics`. Read **S**, the **gap** label, and the component table in 30 seconds.
2. `/` — regime, breadth, volume vs market cap.
3. `/screener` — open a name.
4. `/token/SOL` — RSI, gates, ATR plan.
5. `/sentiment` — F&G vs funding crowding vs liquidation side.
6. `/api/overview` and `/api/analytics` — same desks as JSON.
7. `/claw` — “Is the crowd hotter than BTC funding?”

---

## Social post (optional award)

Draft: screenshot of Analytics (S + gap). Tag @ryodigital. “Soundings reads Fear & Greed against BTC funding from live RYO tools — crowd vs tape, no invented OI.” Link the repo.

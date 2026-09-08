from __future__ import annotations

from typing import Any

from .extract import as_number


def market_cards(overview: dict[str, Any], sentiment: dict[str, Any], scan_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    totals = overview.get("totals") if isinstance(overview.get("totals"), dict) else {}
    vol = as_number(totals.get("total_volume_24h_usd")) or as_number(overview.get("total_volume_24h_usd"))
    cap = as_number(totals.get("total_market_cap_usd")) or as_number(overview.get("total_market_cap_usd"))
    if vol is not None and cap not in (None, 0):
        turn = vol / cap
        cards.append(
            {
                "title": "Market turnover",
                "body": f"24h volume is {turn * 100:.2f}% of total market cap.",
                "tone": "warn" if turn >= 0.04 else "ok",
            }
        )
    btc = as_number(overview.get("btc_dominance"))
    eth = as_number(overview.get("eth_dominance"))
    if btc is not None:
        rest = 100.0 - btc - (eth or 0)
        cards.append(
            {
                "title": "Dominance split",
                "body": f"BTC {btc:.1f}% · ETH {eth:.1f}% · rest {rest:.1f}%." if eth is not None else f"BTC {btc:.1f}%.",
                "tone": "ok",
            }
        )
    fg = as_number(overview.get("fear_greed"))
    if fg is None:
        fg = as_number(sentiment.get("fear_greed"))
    regime = (overview.get("regime") or "").lower()
    if fg is not None and fg >= 70 and "neutral" in regime:
        cards.append(
            {
                "title": "Greed vs regime",
                "body": f"Fear & Greed {fg:.0f} (greed). Regime {overview.get('regime')}.",
                "tone": "warn",
            }
        )
    alt = (sentiment.get("altseason") or {}).get("phase")
    if btc is not None and btc >= 55 and alt in {"transition", "bitcoin", "btc"}:
        cards.append(
            {
                "title": "BTC-led tape",
                "body": f"BTC dominance {btc:.1f}%. Altseason phase “{alt}”.",
                "tone": "warn",
            }
        )
    fund = sentiment.get("funding") or {}
    if (fund.get("crowding") or "") == "crowded" and fg is not None and fg >= 65:
        cards.append(
            {
                "title": "Crowded greed",
                "body": "Funding is crowded. Fear & Greed is elevated.",
                "tone": "warn",
            }
        )
    if fg is not None and fg >= 70 and (fund.get("crowding") or "") == "normal":
        pctl = as_number(fund.get("percentile_90d"))
        pctl_txt = f" Funding sits at the {pctl:.0f}th percentile of 90 days." if pctl is not None else ""
        cards.append(
            {
                "title": "Surface heat, quiet book",
                "body": f"Fear & Greed {fg:.0f} greed. BTC funding crowding normal.{pctl_txt}",
                "tone": "warn",
            }
        )
    liq = sentiment.get("liquidation") or {}
    dominant = (liq.get("dominant") or "").lower()
    if dominant == "shorts" and fg is not None and fg >= 60:
        share = as_number(liq.get("long_share_pct"))
        share_txt = f" Longs were {share:.0f}% of the notional." if share is not None else ""
        cards.append(
            {
                "title": "Shorts paid",
                "body": f"BTC liquidations dominated by shorts.{share_txt}",
                "tone": "ok",
            }
        )
    if dominant == "longs" and (liq.get("pressure") or "") in {"elevated", "high", "stressed"}:
        cards.append(
            {
                "title": "Longs paid",
                "body": "BTC liquidations dominated by longs. Pressure elevated.",
                "tone": "warn",
            }
        )
    adv = overview.get("advancing")
    dec = overview.get("declining")
    if isinstance(adv, int) and isinstance(dec, int) and adv + dec:
        if fg is not None and fg >= 70 and adv < dec:
            cards.append(
                {
                    "title": "Narrow greed",
                    "body": f"Fear & Greed greedy. Breadth {adv} advancing / {dec} declining.",
                    "tone": "warn",
                }
            )
        elif adv > dec:
            cards.append(
                {
                    "title": "Breadth",
                    "body": f"{adv} advancing / {dec} declining across a {overview.get('universe') or 'listed'} universe.",
                    "tone": "ok",
                }
            )
    mcap_chg = as_number(overview.get("mcap_change_24h"))
    if mcap_chg is not None and fg is not None and fg >= 70 and mcap_chg < 0:
        cards.append(
            {
                "title": "Greed on a down tape",
                "body": f"Fear & Greed is {fg:.0f} while total market cap is {mcap_chg:+.2f}% on the day.",
                "tone": "warn",
            }
        )
    spikes = [
        r
        for r in scan_rows
        if (r.get("change_24h") is not None and abs(r["change_24h"]) >= 80)
        or (r.get("turnover") is not None and r["turnover"] >= 1)
    ]
    if spikes:
        names = ", ".join(r["symbol"] for r in spikes[:4] if r.get("symbol"))
        cards.append({"title": "Spikes", "body": f"{names} — turnover ≥ 1 or a ≥80% day.", "tone": "warn"})
    crowding = fund.get("crowding") or "normal"
    pressure = liq.get("pressure") or "normal"
    if crowding == "normal" and pressure == "normal" and sentiment.get("material_shift") is False:
        cards.append(
            {
                "title": "No material stress",
                "body": "Fear & Greed 7d unchanged. Funding and liquidation pressure normal.",
                "tone": "ok",
            }
        )
    wow = as_number(fund.get("wow_pct"))
    if wow is not None and abs(wow) >= 15:
        cards.append(
            {
                "title": "Funding week-on-week",
                "body": f"BTC 7-day funding mean moved {wow:+.1f}% versus the prior week.",
                "tone": "warn" if wow > 0 else "ok",
            }
        )
    alt_idx = as_number((sentiment.get("altseason") or {}).get("index"))
    if alt_idx is not None:
        cards.append(
            {
                "title": "Altseason index",
                "body": f"Altseason index {alt_idx:.0f}, phase “{alt or 'unknown'}”.",
                "tone": "ok" if alt_idx < 75 else "warn",
            }
        )
    return cards


def gap_cards(stress: dict[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(stress, dict):
        return []
    gap = stress.get("gap") if isinstance(stress.get("gap"), dict) else {}
    if not gap.get("body"):
        return []
    code = gap.get("code") or ""
    tone = "ok"
    if code in {"crowd_hotter_than_tape", "tape_hotter_than_crowd", "aligned_froth", "crowd_hot"}:
        tone = "warn"
    return [{"title": gap.get("label") or "Crowd vs tape", "body": gap["body"], "tone": tone}]


def token_cards(token: dict[str, Any], deep: dict[str, Any]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    h24 = as_number(token.get("change_24h"))
    d30 = as_number(token.get("change_30d"))
    if h24 is not None and d30 is not None and ((h24 > 0 and d30 < 0) or (h24 < 0 and d30 > 0)):
        cards.append(
            {
                "title": "Horizon conflict",
                "body": f"24h {h24:+.1f}% vs 30d {d30:+.1f}%.",
                "tone": "warn",
            }
        )
    h7 = as_number(token.get("change_7d"))
    if h24 is not None and h7 is not None and ((h24 > 0 and h7 < 0) or (h24 < 0 and h7 > 0)):
        cards.append(
            {
                "title": "Week vs day",
                "body": f"24h {h24:+.1f}% against 7d {h7:+.1f}%.",
                "tone": "mute",
            }
        )
    rsi = as_number(token.get("rsi_14"))
    trend = (token.get("trend") or "").lower()
    if rsi is not None and rsi >= 70 and trend == "up":
        cards.append({"title": "Overbought uptrend", "body": f"Trend is up. RSI(14) {rsi:.1f}.", "tone": "warn"})
    if rsi is not None and 60 <= rsi < 70 and trend == "up":
        cards.append({"title": "Uptrend", "body": f"Trend is up. RSI(14) {rsi:.1f}.", "tone": "ok"})
    if rsi is not None and rsi <= 30 and trend == "down":
        cards.append({"title": "Oversold downtrend", "body": f"Trend is down. RSI(14) {rsi:.1f}.", "tone": "warn"})
    turn = as_number(token.get("turnover"))
    if turn is not None and turn >= 1:
        cards.append({"title": "Crowded name", "body": f"24h volume is {turn:.2f}× market cap.", "tone": "warn"})
    elif turn is not None and turn >= 0.1:
        cards.append({"title": "Active book", "body": f"24h volume is {turn:.2f}× market cap.", "tone": "ok"})
    dil = as_number(token.get("dilution"))
    if dil is not None and dil >= 0.2:
        cards.append({"title": "Dilution gap", "body": f"FDV is {dil * 100:.0f}% above circulating market cap.", "tone": "mute"})
    atr = as_number(token.get("atr_14_pct"))
    if atr is not None and atr >= 8:
        cards.append({"title": "Wide ATR", "body": f"ATR(14) {atr:.2f}% of price.", "tone": "warn"})
    rank = as_number(token.get("rank"))
    if rank is not None and rank <= 10:
        cards.append({"title": "Top-10 book", "body": f"Rank {int(rank)} by market cap on this scan.", "tone": "ok"})
    gates = deep.get("gates") if isinstance(deep.get("gates"), list) else []
    failed = [g.get("name") for g in gates if isinstance(g, dict) and g.get("passed") is False]
    passed = [g.get("name") for g in gates if isinstance(g, dict) and g.get("passed") is True]
    if failed or passed:
        cards.append({"title": "Confluence gates", "body": f"Passed: {', '.join(str(n) for n in passed) or 'none'}. Failed: {', '.join(str(n) for n in failed) or 'none'}.", "tone": "warn" if failed else "ok"})
    if deep.get("derivatives") is None and deep.get("status") in {"ok", "partial"}:
        cards.append({"title": "Derivatives", "body": "Unavailable.", "tone": "mute"})
    return cards

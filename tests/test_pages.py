import re

from conftest import DOWN, SENTIMENT, envelope

from app import insights
from app.extract import extract_overview, first_number


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_overview_breadth_is_advancing_vs_declining(ryo_replies, client):
    ryo_replies()
    html = client.get("/").text
    card = re.search(r"Market breadth</label>(.*?)</article>", html, re.S).group(1)
    assert re.findall(r'class="val (?:up|down)">([^<]+)<', card) == ["84", "8"]
    assert "n=92" in card


def test_gap_and_insights_agree_on_funding(ryo_replies, client):
    """Percentile rule: 84th percentile is crowded everywhere, whatever RYO's own flag says."""
    ryo_replies()
    a = client.get("/api/analytics").json()
    assert a["stress"]["tape"]["label"] == "crowded"
    assert a["stress"]["gap"]["label"] == "Aligned froth"
    page = _text(client.get("/insights").text)
    assert "crowding normal" not in page
    assert "Funding is crowded" in page


def test_tape_label_shown_with_rule_and_ryo_flag(ryo_replies, client):
    ryo_replies()
    page = _text(client.get("/analytics").text)
    assert "BTC funding crowded · 90d pctl 84 (≥ 70 crowded, ≤ 30 uncrowded; RYO flag normal)" in page
    sentiment = _text(client.get("/sentiment").text)
    assert "crowded p84 of 90d · RYO flag normal" in sentiment


def test_outage_never_prints_none_or_invents_stable(ryo_replies, client):
    ryo_replies({"monitor_market_sentiment_shift": DOWN, "market_overview": DOWN})
    sentiment = _text(client.get("/sentiment").text)
    assert "None" not in sentiment
    assert "7d stable" not in sentiment
    analytics = _text(client.get("/analytics").text)
    assert "7d stable" not in analytics and "None" not in analytics


def test_banner_names_feeds_on_last_good_and_down(ryo_replies, client):
    last_good = envelope(SENTIMENT, stale=True, ok=False, error={"message": "down", "code": "upstream_degraded"})
    ryo_replies({"monitor_market_sentiment_shift": last_good, "scan_market": DOWN})
    page = _text(client.get("/").text)
    assert "RYO is not answering for sentiment (from 2026-09-21 11:07 UTC). Showing the last good reading." in page
    assert "No data from RYO for scan right now. Those fields stay blank." in page
    feeds = client.get("/api/overview").json()["feeds"]
    assert feeds == {"last_good": ["sentiment (from 2026-09-21 11:07 UTC)"], "down": ["scan"]}


def test_no_banner_when_all_feeds_answer(ryo_replies, client):
    ryo_replies()
    for path in ["/", "/analytics", "/screener", "/sentiment", "/insights", "/claw"]:
        assert "feed-banner" not in client.get(path).text, path


def test_every_page_renders_during_a_full_outage(ryo_replies, client):
    down = {t: DOWN for t in ["market_overview", "monitor_market_sentiment_shift", "scan_market"]}
    ryo_replies(down)
    for path in ["/", "/analytics", "/screener", "/sentiment", "/insights", "/api/overview", "/api/analytics", "/api/screener"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "None" not in _text(r.text) or path.startswith("/api"), path


def test_zero_is_a_value_not_missing():
    assert first_number(0, 5) == 0
    assert first_number(None, "", 5) == 5
    env = envelope({"status": "ok", "data": {"sentiment": {"fear_greed_index": 0}, "fear_greed_index": 50}})
    assert extract_overview(env)["fear_greed"] == 0


def test_no_material_stress_needs_real_values():
    """Missing liquidation pressure is not 'normal'."""
    cards = insights.market_cards({}, {"material_shift": False, "liquidation": {}}, [], tape="normal")
    assert not any(c["title"] == "No material stress" for c in cards)

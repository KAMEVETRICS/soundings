from app.tickers import parse_symbol


def test_blank_is_empty() -> None:
    assert parse_symbol("")["empty"] is True
    assert parse_symbol(None)["empty"] is True


def test_strips_pair_suffix() -> None:
    assert parse_symbol("solusdt")["symbol"] == "SOL"
    assert parse_symbol("btc/usdt")["symbol"] == "BTC"


def test_rejects_junk() -> None:
    parsed = parse_symbol("!!!")
    assert parsed["ok"] is False
    assert parsed["code"] == "bad_shape"

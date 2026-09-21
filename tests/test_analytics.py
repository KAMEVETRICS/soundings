from app.analytics import positioning_stress, z_from_center


def test_z_from_center() -> None:
    assert z_from_center(50) == 0
    assert z_from_center(75) == 1.0
    assert z_from_center(None) is None


def test_crowd_hotter_than_tape() -> None:
    pack = positioning_stress(
        {"fear_greed": 80, "regime": "risk-on"},
        {"fear_greed": 80, "funding": {"percentile_90d": 20, "crowding": "uncrowded"}},
    )
    assert pack["gap"]["code"] == "crowd_hotter_than_tape"
    assert pack["S"] is not None
    assert pack["crowd"]["label"] == "greed"
    assert pack["tape"]["label"] == "uncrowded"


def test_missing_fields_stay_blank() -> None:
    pack = positioning_stress({}, {})
    assert pack["S"] is None
    assert pack["reading"] == "unavailable"

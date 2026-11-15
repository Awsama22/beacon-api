from datetime import UTC, datetime, timedelta

from services.refresh_service import period_for
from utilities.live_payload_util import build_live_payload
from utilities.static_source_util import grid_key

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


def row(lat, lon, frp, source, satellite, hours_ago, level="nominal", day="D", static=False):
    acquired = NOW - timedelta(hours=hours_ago)
    return (lat, lon, frp, source, satellite, acquired, level, day, static)


def test_live_payload_bins_counts_and_statics():
    rows = [
        # Two VIIRS NOAA-20 detections in the same 0.1° bin outside the GCC: one point, n=2,
        # placed at the stronger one, with the most recent hours.
        row(-14.371, 30.257, 5.0, "VIIRS_NOAA20_NRT", "N20", 10),
        row(-14.372, 30.258, 9.0, "VIIRS_NOAA20_NRT", "N20", 3, level="high", day="N"),
        # MODIS Aqua in the GCC.
        row(24.2, 55.7, 12.0, "MODIS_NRT", "A", 1),
        # A gas flare: counted as static, not as a fire point.
        row(26.0, 50.0, 40.0, "VIIRS_NOAA21_NRT", "N21", 2, static=True),
    ]
    payload = build_live_payload(rows, NOW)
    assert payload["counts"] == {
        "MODIS": 1,
        "VIIRS": 2,
        "gccMODIS": 1,
        "gccVIIRS": 0,
        "gccStatic": 1,
        "static": 1,
    }
    points = [payload["points"][i : i + 8] for i in range(0, len(payload["points"]), 8)]
    assert [-14.372, 30.258, 9.0, 3, 3, 2, 0, 2] in points
    assert [24.2, 55.7, 12.0, 1, 1, 1, 1, 1] in points
    assert payload["statics"] == [26.0, 50.0, 40.0, 4, 2, 1, 1, 1]
    assert payload["newest"] == "2026-11-13T11:00:00.000Z"
    assert len(payload["cells"]) == 2 * 6


def test_empty_payload_uses_now():
    payload = build_live_payload([], NOW)
    assert payload["points"] == [] and payload["newest"] == payload["generated"]


def test_grid_key_rounds_half_up_like_javascript():
    assert grid_key(26.005) == 2601
    assert grid_key(-0.005) == 0
    assert grid_key(50.0) == 5000


def test_refresh_period_covers_the_gap():
    assert period_for(None) == "7d"
    assert period_for(timedelta(hours=2)) == "24h"
    assert period_for(timedelta(hours=30)) == "48h"
    assert period_for(timedelta(days=3)) == "7d"

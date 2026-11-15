from datetime import UTC, datetime

from constants.firms_constants import ConfidenceLevel, FirmsSource
from utilities.firms_parser_util import confidence_level, parse_detection

MODIS_ROW = {
    "latitude": "24.2",
    "longitude": "55.7",
    "brightness": "320.5",
    "acq_date": "2026-11-12",
    "acq_time": "130",
    "satellite": "Terra",
    "confidence": "85",
    "frp": "12.4",
    "daynight": "N",
}


def test_modis_confidence_maps_to_levels():
    assert confidence_level("10") == ConfidenceLevel.LOW
    assert confidence_level("30") == ConfidenceLevel.NOMINAL
    assert confidence_level("79") == ConfidenceLevel.NOMINAL
    assert confidence_level("80") == ConfidenceLevel.HIGH


def test_viirs_confidence_letters_and_words():
    assert confidence_level("l") == ConfidenceLevel.LOW
    assert confidence_level("n") == ConfidenceLevel.NOMINAL
    assert confidence_level("high") == ConfidenceLevel.HIGH
    assert confidence_level("?") is None


def test_parse_modis_row():
    detection = parse_detection(MODIS_ROW, FirmsSource.MODIS_NRT)
    assert detection["sensor"] == "MODIS"
    assert detection["acquired_at"] == datetime(2026, 11, 12, 1, 30, tzinfo=UTC)
    assert detection["brightness"] == 320.5
    assert detection["confidence_level"] == ConfidenceLevel.HIGH
    assert detection["fire_type"] is None
    assert detection["is_static_source"] is None


def test_parse_viirs_archive_row_marks_static_sources():
    row = {**MODIS_ROW, "bright_ti4": "330", "confidence": "n", "type": "2"}
    del row["brightness"]
    detection = parse_detection(row, FirmsSource.VIIRS_SNPP_SP)
    assert detection["sensor"] == "VIIRS"
    assert detection["brightness"] == 330
    assert detection["fire_type"] == 2
    assert detection["is_static_source"] is True


def test_parse_skips_broken_rows():
    assert parse_detection({**MODIS_ROW, "latitude": "x"}, FirmsSource.MODIS_NRT) is None
    assert parse_detection({**MODIS_ROW, "confidence": ""}, FirmsSource.MODIS_NRT) is None

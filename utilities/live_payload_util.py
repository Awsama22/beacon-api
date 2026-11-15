"""Builds the website's compact live.json shape from stored detections.

A port of the live() step in the website's scripts/fetch-data.mjs, so the website can read
GET /fires/live instead of its bundled file without any other change.
"""

from datetime import datetime
from math import floor

from constants.firms_constants import CONFIDENCE_RANK, FirmsSource, sensor_of
from utilities.static_source_util import grid_key

SATELLITES = ["Terra MODIS", "Aqua MODIS", "Suomi NPP VIIRS", "NOAA-20 VIIRS", "NOAA-21 VIIRS"]
FIELDS = ["lat", "lon", "frp", "sat", "hoursAgo", "conf", "day", "n"]
VIIRS_SATELLITE_INDEX = {
    FirmsSource.VIIRS_SNPP_NRT: 2,
    FirmsSource.VIIRS_NOAA20_NRT: 3,
    FirmsSource.VIIRS_NOAA21_NRT: 4,
}
GCC_BOX = (12.0, 33.0, 34.0, 60.5)  # south, north, west, east


def round_half_up(value: float, digits: int) -> float:
    scale = 10**digits
    return floor(value * scale + 0.5) / scale


def iso(moment: datetime) -> str:
    """Like JavaScript's toISOString: milliseconds and a Z."""
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def satellite_index(source: FirmsSource, satellite: str) -> int:
    if source == FirmsSource.MODIS_NRT:
        return 0 if satellite.startswith("T") else 1
    return VIIRS_SATELLITE_INDEX[source]


def add(table: dict, key, item: list, raw_frp: float, *, move: bool) -> None:
    """Start a bin with item, or merge item into it. The JS compares the raw FRP with the stored
    (rounded) one; with move, a stronger detection also takes over the place and details."""
    current = table.setdefault(key, item)
    if current is item:
        return
    current[7] += 1
    current[4] = min(current[4], item[4])
    if raw_frp > current[2]:
        if move:
            current[:4] = item[:4]
            current[5:7] = item[5:7]
        else:
            current[2] = item[2]


def build_live_payload(rows, now: datetime) -> dict:
    """rows: (latitude, longitude, frp, source, satellite, acquired_at, confidence_level,
    day_night, is_static_source), low confidence already left out."""
    bins: dict[str, list] = {}
    statics: dict[tuple[int, int], list] = {}
    cells: dict[int, list[int]] = {}
    counts = {"MODIS": 0, "VIIRS": 0, "gccMODIS": 0, "gccVIIRS": 0, "gccStatic": 0, "static": 0}
    newest = oldest = None
    south, north, west, east = GCC_BOX
    for latitude, longitude, frp, source, satellite, acquired_at, level, day_night, static in rows:
        newest = max(newest or acquired_at, acquired_at)
        oldest = min(oldest or acquired_at, acquired_at)
        source = FirmsSource(source)
        raw_frp = frp or 0.0
        sat = satellite_index(source, satellite)
        hours = max(0, floor((now - acquired_at).total_seconds() / 3600 + 0.5))
        item = [
            round_half_up(latitude, 3),
            round_half_up(longitude, 3),
            round_half_up(raw_frp, 1),
            sat,
            hours,
            CONFIDENCE_RANK[level],
            1 if day_night == "D" else 0,
            1,
        ]
        gcc = south <= latitude <= north and west <= longitude <= east
        if static:
            counts["static"] += 1
            counts["gccStatic"] += gcc
            add(statics, (grid_key(latitude), grid_key(longitude)), item, raw_frp, move=False)
            continue
        family = sensor_of(source)
        counts[family] += 1
        counts[f"gcc{family}"] += gcc
        row = min(719, floor((90 - latitude) / 0.25))
        cell = row * 1440 + min(1439, floor((longitude + 180) / 0.25))
        cells.setdefault(cell, [0, 0, 0, 0, 0])[sat] += 1
        size = 0.02 if gcc else 0.1
        add(
            bins,
            f"{family}|{floor(latitude / size)},{floor(longitude / size)}",
            item,
            raw_frp,
            move=True,
        )
    return {
        "generated": iso(now),
        "newest": iso(newest or now),
        "oldest": iso(oldest or now),
        "fields": FIELDS,
        "satellites": SATELLITES,
        "counts": counts,
        "points": [value for item in bins.values() for value in item],
        "statics": [value for item in statics.values() for value in item],
        "cells": [value for key, item in cells.items() for value in (key, *item)],
    }

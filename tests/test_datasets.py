from fastapi import Request

from services.dataset_import_service import grid_rows, history_rows
from services.dataset_service import pack_grid
from utilities.cached_body_util import body_response, cached_json


def request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw})


def test_grid_round_trips_through_the_binary_format():
    cells = [(10, 20, [0, 5, 65535]), (11, 700, [1, 2, 3])]
    rows = list(grid_rows(pack_grid(cells)))
    assert rows == [{"row": r, "col": c, "yearly": y} for r, c, y in cells]


def test_empty_grid_has_only_a_header():
    assert list(grid_rows(pack_grid([]))) == []


def test_history_values_are_stored_as_floats():
    [row] = history_rows([{"lat": 1.0, "lon": 2.0, "c": "Oman", "a": [3, 4.5], "m": [0], "t": 7}])
    assert row["annual"] == [3.0, 4.5] and all(isinstance(v, float) for v in row["annual"])


def test_cached_body_answers_304_and_gzip():
    body = cached_json({"a": 1})
    assert body_response(request({"If-None-Match": body.etag}), body).status_code == 304
    zipped = body_response(request({"Accept-Encoding": "gzip"}), body)
    assert zipped.headers["content-encoding"] == "gzip" and zipped.body == body.gzip
    assert body_response(request({}), body).body == b'{"success":true,"data":{"a":1},"error":null}'

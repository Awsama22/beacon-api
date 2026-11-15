"""Pre-encoded response bodies for large, rarely changing payloads.

A body is encoded and gzipped once and kept until its version changes; requests only send the
stored bytes, answer 304 when the browser already has them, and let browsers reuse them for
5 minutes.
"""

import gzip
import hashlib
import json
import threading
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response

from utilities.api_response_util import success_response


@dataclass(frozen=True)
class CachedBody:
    gzip: bytes  # only the gzipped bytes are kept; nearly every client accepts gzip
    etag: str
    media_type: str

    @property
    def raw(self) -> bytes:
        return gzip.decompress(self.gzip)


def cached_body(raw: bytes, media_type: str = "application/octet-stream") -> CachedBody:
    etag = f'"{hashlib.blake2b(raw, digest_size=12).hexdigest()}"'
    return CachedBody(gzip.compress(raw, 6), etag, media_type)


def cached_json(data: Any) -> CachedBody:
    """`data` wrapped in the usual {success, data, error} body."""
    raw = json.dumps(success_response(data), separators=(",", ":")).encode()
    return cached_body(raw, "application/json")


class VersionedCache:
    """Bodies by key, each rebuilt when its version (e.g. the last import time) changes.
    One build per key at a time; other keys don't wait for it."""

    def __init__(self) -> None:
        self.bodies: dict[str, tuple[Hashable, CachedBody]] = {}
        self.locks: dict[str, threading.Lock] = {}

    def get(self, key: str, version: Hashable, build: Callable[[], CachedBody]) -> CachedBody:
        hit = self.bodies.get(key)
        if hit and hit[0] == version:
            return hit[1]
        with self.locks.setdefault(key, threading.Lock()):
            hit = self.bodies.get(key)
            if not (hit and hit[0] == version):
                self.bodies[key] = hit = (version, build())
            return hit[1]


def body_response(request: Request, body: CachedBody) -> Response:
    headers = {"Cache-Control": "public, max-age=300", "ETag": body.etag, "Vary": "Accept-Encoding"}
    if request.headers.get("if-none-match") == body.etag:
        return Response(status_code=304, headers=headers)
    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
        return Response(body.gzip, media_type=body.media_type, headers=headers)
    return Response(body.raw, media_type=body.media_type, headers=headers)

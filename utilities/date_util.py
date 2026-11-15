from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

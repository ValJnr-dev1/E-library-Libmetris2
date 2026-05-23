from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def minutes_between(start: datetime, end: datetime) -> int:
    delta = _as_utc(end) - _as_utc(start)
    return max(0, int(delta.total_seconds() / 60))

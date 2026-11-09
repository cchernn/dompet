from datetime import datetime

from ..lib.exceptions import InvalidDataException

VALID_BUCKETS = ("day", "week", "month")


def parse_bucket(value) -> str:
    bucket = value or "day"
    if bucket not in VALID_BUCKETS:
        raise InvalidDataException(ValueError(f"bucket must be one of: {', '.join(VALID_BUCKETS)}"))
    return bucket


def bucket_label(bucket: str, period_start: datetime) -> str:
    """Backend-formatted so the frontend never has to reconstruct a label
    from period_start itself: 'day' -> '10 Mar', 'week' -> the ISO week's
    Monday as 'Week of Mar 3', 'month' -> 'Mar 2026'."""
    if bucket == "day":
        return f"{period_start.day} {period_start.strftime('%b')}"
    if bucket == "week":
        return f"Week of {period_start.strftime('%b')} {period_start.day}"
    return period_start.strftime("%b %Y")

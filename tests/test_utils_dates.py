from datetime import datetime, timedelta, timezone
from src.utils.dates import freshness_tag


def _iso(delta_hours: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=delta_hours)
    return dt.isoformat()


def test_less_than_one_hour():
    assert freshness_tag(_iso(0.5)) == "[<1h ago]"


def test_a_few_hours_ago():
    tag = freshness_tag(_iso(5))
    assert tag == "[5h ago]"


def test_one_day_ago():
    tag = freshness_tag(_iso(25))
    assert tag == "[1d ago]"


def test_empty_string_returns_empty():
    assert freshness_tag("") == ""


def test_invalid_string_returns_empty():
    assert freshness_tag("not-a-date") == ""


def test_naive_datetime_handled():
    # Some sources return naive datetimes — should not crash
    naive_iso = datetime.now().isoformat()  # no tz info
    result = freshness_tag(naive_iso)
    assert result != ""  # should still produce a tag

from datetime import datetime, timedelta, timezone

from app.services.reminders import should_send_reminder


def test_send_reminder_if_missing():
    now = datetime.now(timezone.utc)
    assert should_send_reminder(None, now) is True


def test_send_reminder_once_per_day():
    now = datetime.now(timezone.utc)
    last = now - timedelta(hours=23)
    assert should_send_reminder(last, now) is False


def test_send_reminder_after_day():
    now = datetime.now(timezone.utc)
    last = now - timedelta(hours=25)
    assert should_send_reminder(last, now) is True

from __future__ import annotations

from datetime import datetime, timedelta


def should_send_reminder(last_reminder_at: datetime | None, now: datetime) -> bool:
    if not last_reminder_at:
        return True
    return now - last_reminder_at >= timedelta(hours=24)

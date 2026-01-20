from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventLevel


async def log_event(
    session: AsyncSession,
    event_type: str,
    level: EventLevel = EventLevel.info,
    user_id: int | None = None,
    listing_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    event = Event(
        event_type=event_type,
        level=level,
        user_id=user_id,
        listing_id=listing_id,
        metadata=metadata or {},
    )
    session.add(event)
    await session.commit()

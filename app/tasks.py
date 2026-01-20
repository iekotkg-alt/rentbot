from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import redis.asyncio as redis
from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.events import log_event
from app.models import Listing, ListingState, RentStatus, User
from app.services.listings import build_caption, can_bump
from app.services.reminders import should_send_reminder
from app.telegram.bot_factory import create_bot
from app.telegram.gateway import TelegramGateway
from app.utils.flags import get_flag
from app.utils.locks import redis_lock

celery_app = Celery("rent_bot")
celery_app.conf.broker_url = settings.redis_url
celery_app.conf.result_backend = settings.redis_url
celery_app.conf.timezone = settings.timezone
celery_app.conf.beat_schedule = {
    "bump-listings": {"task": "app.tasks.bump_listings", "schedule": 60 * 30},
    "send-reminders": {"task": "app.tasks.send_reminders", "schedule": 60 * 60},
    "heartbeat-worker": {
        "task": "app.tasks.update_heartbeat",
        "schedule": 60,
        "args": ["worker"],
    },
    "heartbeat-beat": {
        "task": "app.tasks.update_heartbeat",
        "schedule": 60,
        "args": ["beat"],
    },
}

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def _get_gateway():
    bot = create_bot()

    async def session_provider():
        async with SessionLocal() as session:
            yield session

    return TelegramGateway(bot=bot, session_provider=session_provider)


@celery_app.task
def bump_listings() -> None:
    import asyncio

    asyncio.run(_bump_listings())


async def _bump_listings() -> None:
    gateway = await _get_gateway()
    redis_client = redis.from_url(settings.redis_url)
    if await get_flag(redis_client, "pause_bumps") or await get_flag(
        redis_client, "pause_publications"
    ):
        await redis_client.close()
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(Listing).where(
                Listing.state == ListingState.published,
                Listing.rent_status == RentStatus.free,
            )
        )
        listings = result.scalars().all()
        now = datetime.now(timezone.utc)

        for listing in listings:
            async with redis_lock(redis_client, f"bump:{listing.id}", ttl=60) as acquired:
                if not acquired:
                    continue
                if not can_bump(listing, now):
                    continue
                caption = build_caption(listing)
                message = await gateway.send_photo(
                    chat_id=settings.public_channel_id,
                    photo=listing.photo_file_id,
                    caption=caption.text,
                    reply_markup=caption.markup,
                )
                if listing.channel_message_id:
                    await gateway.delete_message(
                        chat_id=listing.channel_chat_id,
                        message_id=listing.channel_message_id,
                    )
                listing.channel_chat_id = settings.public_channel_id
                listing.channel_message_id = message.message_id
                listing.last_bump_at = now
                await session.commit()
                await log_event(
                    session,
                    event_type="listing_bumped",
                    user_id=listing.owner_telegram_user_id,
                    listing_id=listing.id,
                    metadata={"message_id": message.message_id},
                )

    await redis_client.close()


@celery_app.task
def send_reminders() -> None:
    import asyncio

    asyncio.run(_send_reminders())


async def _send_reminders() -> None:
    gateway = await _get_gateway()
    redis_client = redis.from_url(settings.redis_url)
    if await get_flag(redis_client, "pause_reminders"):
        await redis_client.close()
        return
    now = datetime.now(timezone.utc)
    local_time = now.astimezone(ZoneInfo(settings.timezone)).time()
    reminder_time = time.fromisoformat(settings.reminder_time)
    if local_time < reminder_time:
        await redis_client.close()
        return

    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        for user in users:
            async with redis_lock(
                redis_client, f"reminder:{user.telegram_user_id}", ttl=60
            ) as acquired:
                if not acquired:
                    continue
                if not should_send_reminder(user.last_reminder_at, now):
                    continue
                active_listings = await session.execute(
                    select(Listing).where(
                        Listing.owner_telegram_user_id == user.telegram_user_id,
                        Listing.state == ListingState.published,
                    )
                )
                if not active_listings.scalars().first():
                    continue
                await gateway.send_message(
                    chat_id=user.telegram_user_id,
                    text=(
                        "Если автомобиль уже сдан — поставьте статус «Сдана», "
                        "и объявление удалится из канала."
                    ),
                )
                user.last_reminder_at = now
                await session.commit()
                await log_event(
                    session,
                    event_type="reminder_sent",
                    user_id=user.telegram_user_id,
                )

    await redis_client.close()


@celery_app.task
def update_heartbeat(role: str) -> None:
    import asyncio

    asyncio.run(_update_heartbeat(role))


async def _update_heartbeat(role: str) -> None:
    redis_client = redis.from_url(settings.redis_url)
    now = datetime.now(timezone.utc).isoformat()
    await redis_client.set(f"celery:{role}:heartbeat", now, ex=180)
    await redis_client.close()

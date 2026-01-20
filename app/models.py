from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class ListingState(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    needs_changes = "needs_changes"
    published = "published"
    rejected = "rejected"
    archived = "archived"


class RentStatus(str, enum.Enum):
    free = "free"
    booked = "booked"
    rented = "rented"


class EventLevel(str, enum.Enum):
    info = "info"
    warn = "warn"
    error = "error"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listings: Mapped[list[Listing]] = relationship(back_populates="owner")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_telegram_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.telegram_user_id"), index=True
    )
    state: Mapped[ListingState] = mapped_column(
        Enum(ListingState), default=ListingState.draft
    )
    rent_status: Mapped[RentStatus] = mapped_column(Enum(RentStatus), default=RentStatus.free)
    photo_file_id: Mapped[str] = mapped_column(String(256))
    brand_model: Mapped[str] = mapped_column(String(128))
    year: Mapped[str] = mapped_column(String(16))
    city: Mapped[str] = mapped_column(String(64))
    price_text: Mapped[str] = mapped_column(String(64))
    conditions: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    phone_e164: Mapped[str] = mapped_column(String(32))
    tg_username_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    channel_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_bump_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="listings")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_telegram_user_id: Mapped[int] = mapped_column(Integer, index=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    brand_model: Mapped[str] = mapped_column(String(128))
    year: Mapped[str] = mapped_column(String(16))
    city: Mapped[str] = mapped_column(String(64))
    price_text: Mapped[str] = mapped_column(String(64))
    conditions: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    level: Mapped[EventLevel] = mapped_column(Enum(EventLevel), default=EventLevel.info)
    event_type: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listing_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)

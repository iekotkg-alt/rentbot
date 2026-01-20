from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings
from app.models import Listing, RentStatus


@dataclass(slots=True)
class ListingCaption:
    text: str
    markup: InlineKeyboardMarkup


def build_caption(listing: Listing) -> ListingCaption:
    status_map = {
        RentStatus.free: "🟢 Свободна",
        RentStatus.booked: "🟡 Бронь",
        RentStatus.rented: "🔴 Сдана",
    }
    lines = [
        f"{status_map[listing.rent_status]}",
        f"{listing.brand_model}, {listing.year}",
        f"Город: {listing.city}",
        f"Цена: {listing.price_text}",
        f"Условия: {listing.conditions}",
        f"Описание: {listing.description}",
    ]
    caption = "\n".join(lines)

    buttons: list[list[InlineKeyboardButton]] = []
    if listing.tg_username_snapshot:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💬 Telegram", url=f"https://t.me/{listing.tg_username_snapshot}"
                )
            ]
        )
    buttons.append([
        InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{listing.phone_e164}")
    ])

    return ListingCaption(text=caption, markup=InlineKeyboardMarkup(inline_keyboard=buttons))


def can_bump(listing: Listing, now: datetime) -> bool:
    if listing.rent_status != RentStatus.free:
        return False
    if not listing.last_bump_at:
        return True
    return now - listing.last_bump_at >= timedelta(hours=settings.bump_interval_hours)

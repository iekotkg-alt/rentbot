from datetime import datetime, timedelta, timezone

from app.models import Listing, ListingState, RentStatus
from app.services.listings import can_bump


def make_listing(**overrides):
    data = {
        "owner_telegram_user_id": 1,
        "state": ListingState.published,
        "rent_status": RentStatus.free,
        "photo_file_id": "file",
        "brand_model": "Toyota Prius",
        "year": "2020",
        "city": "Минск",
        "price_text": "60 BYN",
        "conditions": "Без залога",
        "description": "Отличное состояние",
        "phone_e164": "+375291234567",
        "tg_username_snapshot": "testuser",
    }
    data.update(overrides)
    return Listing(**data)


def test_can_bump_free_listing():
    listing = make_listing(last_bump_at=None)
    now = datetime.now(timezone.utc)

    assert can_bump(listing, now) is True


def test_can_bump_respects_interval():
    now = datetime.now(timezone.utc)
    listing = make_listing(last_bump_at=now - timedelta(hours=1))

    assert can_bump(listing, now) is False


def test_can_bump_only_free():
    now = datetime.now(timezone.utc)
    listing = make_listing(last_bump_at=now - timedelta(days=2), rent_status=RentStatus.booked)

    assert can_bump(listing, now) is False

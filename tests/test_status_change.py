import pytest

from app.models import Listing, ListingState, RentStatus
from app.services.statuses import apply_status_update


class FakeGateway:
    def __init__(self):
        self.calls = []

    async def edit_message_caption(self, **kwargs):
        self.calls.append(("edit", kwargs))

    async def delete_message(self, **kwargs):
        self.calls.append(("delete", kwargs))


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
        "channel_chat_id": 100,
        "channel_message_id": 200,
    }
    data.update(overrides)
    return Listing(**data)


@pytest.mark.asyncio
async def test_status_change_updates_caption():
    listing = make_listing()
    gateway = FakeGateway()

    result = await apply_status_update(listing, RentStatus.booked, gateway)

    assert result.action == "updated"
    assert listing.rent_status == RentStatus.booked
    assert gateway.calls[0][0] == "edit"


@pytest.mark.asyncio
async def test_status_change_archives_listing():
    listing = make_listing()
    gateway = FakeGateway()

    result = await apply_status_update(listing, RentStatus.rented, gateway)

    assert result.action == "archived"
    assert listing.state == ListingState.archived
    assert gateway.calls[0][0] == "delete"

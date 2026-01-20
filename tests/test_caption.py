from app.models import Listing, ListingState, RentStatus
from app.services.listings import build_caption


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


def test_build_caption_with_username():
    listing = make_listing()
    caption = build_caption(listing)

    assert "Toyota Prius" in caption.text
    assert caption.markup.inline_keyboard[0][0].text == "💬 Telegram"
    assert caption.markup.inline_keyboard[1][0].text == "📞 Позвонить"


def test_build_caption_without_username():
    listing = make_listing(tg_username_snapshot=None)
    caption = build_caption(listing)

    assert caption.markup.inline_keyboard[0][0].text == "📞 Позвонить"
    assert len(caption.markup.inline_keyboard) == 1

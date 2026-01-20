from __future__ import annotations

from dataclasses import dataclass

from app.models import Listing, ListingState, RentStatus
from app.services.listings import build_caption
from app.telegram.gateway import TelegramGateway


@dataclass(slots=True)
class StatusChangeResult:
    action: str


async def apply_status_update(
    listing: Listing, status: RentStatus, gateway: TelegramGateway
) -> StatusChangeResult:
    listing.rent_status = status
    if listing.rent_status == RentStatus.rented:
        if listing.channel_message_id:
            await gateway.delete_message(
                chat_id=listing.channel_chat_id,
                message_id=listing.channel_message_id,
            )
        listing.state = ListingState.archived
        return StatusChangeResult(action="archived")

    caption = build_caption(listing)
    if listing.channel_message_id:
        await gateway.edit_message_caption(
            chat_id=listing.channel_chat_id,
            message_id=listing.channel_message_id,
            caption=caption.text,
            reply_markup=caption.markup,
        )
    return StatusChangeResult(action="updated")

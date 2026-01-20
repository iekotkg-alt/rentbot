from __future__ import annotations

from sqladmin import ModelView

from app.models import Event, Listing, Template, User


class UserAdmin(ModelView, model=User):
    column_list = [User.telegram_user_id, User.username, User.phone_e164, User.created_at]


class ListingAdmin(ModelView, model=Listing):
    column_list = [
        Listing.id,
        Listing.owner_telegram_user_id,
        Listing.state,
        Listing.rent_status,
        Listing.brand_model,
        Listing.city,
        Listing.price_text,
        Listing.created_at,
    ]


class TemplateAdmin(ModelView, model=Template):
    column_list = [Template.id, Template.owner_telegram_user_id, Template.brand_model]


class EventAdmin(ModelView, model=Event):
    column_list = [Event.ts, Event.level, Event.event_type, Event.user_id, Event.listing_id]
    column_default_sort = [(Event.ts, True)]

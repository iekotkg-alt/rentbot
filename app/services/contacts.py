from __future__ import annotations

from aiogram.types import Contact


def is_valid_contact(contact: Contact, user_id: int) -> bool:
    return contact.user_id == user_id

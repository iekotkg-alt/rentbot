from aiogram.types import Contact

from app.services.contacts import is_valid_contact


def test_contact_matches_user():
    contact = Contact(phone_number="123", first_name="Test", user_id=10)
    assert is_valid_contact(contact, 10) is True


def test_contact_mismatch_user():
    contact = Contact(phone_number="123", first_name="Test", user_id=11)
    assert is_valid_contact(contact, 10) is False

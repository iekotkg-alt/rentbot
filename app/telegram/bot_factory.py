from __future__ import annotations

from aiogram import Bot

from app.config import settings


def create_bot() -> Bot:
    return Bot(token=settings.bot_token)

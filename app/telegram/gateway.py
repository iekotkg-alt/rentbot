from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.events import log_event
from app.models import EventLevel


@dataclass(slots=True)
class TelegramGateway:
    bot: Bot
    session_provider: callable

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(TelegramAPIError),
        reraise=True,
    )
    async def send_photo(self, **kwargs):
        return await self._call("send_photo", **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(TelegramAPIError),
        reraise=True,
    )
    async def edit_message_caption(self, **kwargs):
        return await self._call("edit_message_caption", **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(TelegramAPIError),
        reraise=True,
    )
    async def delete_message(self, **kwargs):
        return await self._call("delete_message", **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type(TelegramAPIError),
        reraise=True,
    )
    async def send_message(self, **kwargs):
        return await self._call("send_message", **kwargs)

    async def _call(self, method_name: str, **kwargs):
        try:
            method = getattr(self.bot, method_name)
            return await method(**kwargs)
        except TelegramAPIError as exc:
            async for session in self.session_provider():
                await log_event(
                    session,
                    event_type="telegram_api_error",
                    level=EventLevel.error,
                    metadata={"method": method_name, "error": str(exc)},
                )
            raise

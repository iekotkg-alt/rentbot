from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.events import log_event
from app.models import Listing, ListingState, RentStatus, User
from app.services.contacts import is_valid_contact
from app.services.listings import build_caption, can_bump
from app.services.statuses import apply_status_update
from app.telegram.gateway import TelegramGateway
from app.utils.flags import get_flag, set_flag

router = Router()


class ListingForm(StatesGroup):
    photo = State()
    brand_model = State()
    year = State()
    city = State()
    price_text = State()
    conditions = State()
    description = State()
    contact = State()


def listing_action_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Свободна", callback_data=f"status:free:{listing_id}")],
            [InlineKeyboardButton(text="🟡 Бронь", callback_data=f"status:booked:{listing_id}")],
            [InlineKeyboardButton(text="🔴 Сдана", callback_data=f"status:rented:{listing_id}")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{listing_id}")],
            [InlineKeyboardButton(text="⬆️ Поднять", callback_data=f"bump:{listing_id}")],
        ]
    )


@router.message(Command("start"))
async def start(message: Message, session: AsyncSession) -> None:
    await get_or_create_user(message, session)
    await message.answer(
        "Добро пожаловать! Используйте /new чтобы создать объявление. "
        "Управление объявлениями доступно в меню после публикации."
    )


@router.message(Command("new"))
async def new_listing(message: Message, state: FSMContext) -> None:
    await state.set_state(ListingForm.photo)
    await message.answer("Отправьте одно фото автомобиля.")


@router.message(ListingForm.photo, F.content_type == ContentType.PHOTO)
async def listing_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)
    await state.set_state(ListingForm.brand_model)
    await message.answer("Марка и модель?")


@router.message(ListingForm.brand_model)
async def listing_brand(message: Message, state: FSMContext) -> None:
    await state.update_data(brand_model=message.text.strip())
    await state.set_state(ListingForm.year)
    await message.answer("Год выпуска?")


@router.message(ListingForm.year)
async def listing_year(message: Message, state: FSMContext) -> None:
    await state.update_data(year=message.text.strip())
    await state.set_state(ListingForm.city)
    await message.answer("Город?")


@router.message(ListingForm.city)
async def listing_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text.strip())
    await state.set_state(ListingForm.price_text)
    await message.answer("Цена (текстом, например 60 BYN/сутки)?")


@router.message(ListingForm.price_text)
async def listing_price(message: Message, state: FSMContext) -> None:
    await state.update_data(price_text=message.text.strip())
    await state.set_state(ListingForm.conditions)
    await message.answer("Условия аренды?")


@router.message(ListingForm.conditions)
async def listing_conditions(message: Message, state: FSMContext) -> None:
    await state.update_data(conditions=message.text.strip())
    await state.set_state(ListingForm.description)
    await message.answer("Описание?")


@router.message(ListingForm.description)
async def listing_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(ListingForm.contact)
    await message.answer(
        "Поделитесь контактом кнопкой ниже.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )


@router.message(ListingForm.contact, F.contact)
async def listing_contact(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    gateway: TelegramGateway,
) -> None:
    if not is_valid_contact(message.contact, message.from_user.id):
        await message.answer("Контакт должен принадлежать вам. Попробуйте снова.")
        return
    data = await state.get_data()
    await state.clear()
    user = await get_or_create_user(message, session)
    user.phone_e164 = message.contact.phone_number
    user.username = message.from_user.username

    editing_listing_id = data.get("editing_listing_id")
    if editing_listing_id:
        listing = await session.get(Listing, int(editing_listing_id))
        if listing and listing.owner_telegram_user_id == user.telegram_user_id:
            if listing.channel_message_id:
                await gateway.delete_message(
                    chat_id=listing.channel_chat_id,
                    message_id=listing.channel_message_id,
                )
            listing.photo_file_id = data["photo_file_id"]
            listing.brand_model = data["brand_model"]
            listing.year = data["year"]
            listing.city = data["city"]
            listing.price_text = data["price_text"]
            listing.conditions = data["conditions"]
            listing.description = data["description"]
            listing.phone_e164 = message.contact.phone_number
            listing.tg_username_snapshot = message.from_user.username
            listing.state = ListingState.pending
            listing.channel_message_id = None
            listing.channel_chat_id = None
            await session.commit()
            await log_event(
                session,
                event_type="listing_updated",
                user_id=user.telegram_user_id,
                listing_id=listing.id,
            )
            await message.answer(
                "Изменения отправлены на модерацию. "
                "Мы уведомим вас о решении.",
                reply_markup=None,
            )
            return

    listing = Listing(
        owner_telegram_user_id=user.telegram_user_id,
        photo_file_id=data["photo_file_id"],
        brand_model=data["brand_model"],
        year=data["year"],
        city=data["city"],
        price_text=data["price_text"],
        conditions=data["conditions"],
        description=data["description"],
        phone_e164=message.contact.phone_number,
        tg_username_snapshot=message.from_user.username,
        state=ListingState.pending,
    )
    session.add(listing)
    await session.commit()
    await log_event(
        session,
        event_type="listing_created",
        user_id=user.telegram_user_id,
        listing_id=listing.id,
    )
    await message.answer(
        "Спасибо! Объявление отправлено на модерацию. "
        "Мы уведомим вас о решении.",
        reply_markup=None,
    )


async def build_admin_menu(redis_client: redis.Redis) -> InlineKeyboardMarkup:
    pause_bumps = await get_flag(redis_client, "pause_bumps")
    pause_reminders = await get_flag(redis_client, "pause_reminders")
    pause_publications = await get_flag(redis_client, "pause_publications")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="🧯 Ошибки за 24ч", callback_data="admin:errors")],
            [InlineKeyboardButton(text="❤️ Состояние сервисов", callback_data="admin:services")],
            [InlineKeyboardButton(text="🕒 Очередь модерации", callback_data="admin:queue")],
            [
                InlineKeyboardButton(
                    text=f"Пауза поднятий: {'ON' if pause_bumps else 'OFF'}",
                    callback_data="admin:toggle:pause_bumps",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Пауза напоминаний: {'ON' if pause_reminders else 'OFF'}",
                    callback_data="admin:toggle:pause_reminders",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Пауза публикаций: {'ON' if pause_publications else 'OFF'}",
                    callback_data="admin:toggle:pause_publications",
                )
            ],
        ]
    )


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user.id not in settings.admin_id_set:
        return
    redis_client = redis.from_url(settings.redis_url)
    keyboard = await build_admin_menu(redis_client)
    await redis_client.close()
    await message.answer("Админ-меню:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("admin:"))
async def admin_actions(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user.id not in settings.admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, action, *rest = callback.data.split(":")
    redis_client = redis.from_url(settings.redis_url)
    if action == "stats":
        published = await session.execute(
            select(Listing).where(Listing.state == ListingState.published)
        )
        pending = await session.execute(
            select(Listing).where(Listing.state == ListingState.pending)
        )
        await callback.message.answer(
            f"Активных: {len(published.scalars().all())}\n"
            f"В модерации: {len(pending.scalars().all())}"
        )
    elif action == "errors":
        await callback.message.answer("Ошибки за 24 часа доступны в веб-админке.")
    elif action == "services":
        redis_ok = "OK" if await redis_client.ping() else "FAIL"
        worker = await redis_client.get("celery:worker:heartbeat")
        beat = await redis_client.get("celery:beat:heartbeat")
        await callback.message.answer(
            "Состояние сервисов:\n"
            f"DB: OK\n"
            f"Redis: {redis_ok}\n"
            f"Celery worker: {'OK' if worker else 'FAIL'}\n"
            f"Celery beat: {'OK' if beat else 'FAIL'}"
        )
    elif action == "queue":
        result = await session.execute(
            select(Listing).where(Listing.state == ListingState.pending).limit(5)
        )
        pending = result.scalars().all()
        if not pending:
            await callback.message.answer("Очередь модерации пуста.")
        else:
            for listing in pending:
                await callback.message.answer(
                    f"Заявка #{listing.id}: {listing.brand_model}",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="✅ Одобрить",
                                    callback_data=f"moderate:approve:{listing.id}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="✏️ Нужны правки",
                                    callback_data=f"moderate:changes:{listing.id}",
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    text="❌ Отклонить",
                                    callback_data=f"moderate:reject:{listing.id}",
                                )
                            ],
                        ]
                    ),
                )
    elif action == "toggle" and rest:
        flag = rest[0]
        current = await get_flag(redis_client, flag)
        await set_flag(redis_client, flag, not current)
        await callback.message.answer(f"{flag} переключен на {'ON' if not current else 'OFF'}")
    else:
        await callback.message.answer("Неизвестная команда.")
    keyboard = await build_admin_menu(redis_client)
    await redis_client.close()
    await callback.message.answer("Админ-меню:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("moderate:"))
async def moderate_listing(
    callback: CallbackQuery,
    session: AsyncSession,
    gateway: TelegramGateway,
) -> None:
    if callback.from_user.id not in settings.admin_id_set:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, action, listing_id = callback.data.split(":")
    listing = await session.get(Listing, int(listing_id))
    if not listing:
        await callback.answer("Объявление не найдено", show_alert=True)
        return

    if action == "approve":
        redis_client = redis.from_url(settings.redis_url)
        if await get_flag(redis_client, "pause_publications"):
            await redis_client.close()
            await callback.answer("Публикации на паузе", show_alert=True)
            return
        await redis_client.close()
        caption = build_caption(listing)
        message = await gateway.send_photo(
            chat_id=settings.public_channel_id,
            photo=listing.photo_file_id,
            caption=caption.text,
            reply_markup=caption.markup,
        )
        listing.state = ListingState.published
        listing.published_at = datetime.now(timezone.utc)
        listing.channel_chat_id = settings.public_channel_id
        listing.channel_message_id = message.message_id
        listing.last_bump_at = listing.published_at
        await session.commit()
        await gateway.send_message(
            chat_id=listing.owner_telegram_user_id,
            text="Объявление прошло модерацию и опубликовано.",
            reply_markup=listing_action_keyboard(listing.id),
        )
        await callback.answer("Опубликовано")
        await log_event(
            session,
            event_type="listing_approved",
            user_id=listing.owner_telegram_user_id,
            listing_id=listing.id,
        )
    elif action == "changes":
        listing.state = ListingState.needs_changes
        await session.commit()
        await gateway.send_message(
            chat_id=listing.owner_telegram_user_id,
            text="Нужны правки. Отредактируйте объявление через бота и отправьте снова.",
        )
        await callback.answer("Нужны правки")
        await log_event(
            session,
            event_type="listing_needs_changes",
            user_id=listing.owner_telegram_user_id,
            listing_id=listing.id,
        )
    else:
        listing.state = ListingState.rejected
        await session.commit()
        await gateway.send_message(
            chat_id=listing.owner_telegram_user_id,
            text="К сожалению, объявление отклонено модератором.",
        )
        await callback.answer("Отклонено")
        await log_event(
            session,
            event_type="listing_rejected",
            user_id=listing.owner_telegram_user_id,
            listing_id=listing.id,
        )


@router.callback_query(F.data.startswith("status:"))
async def update_status(
    callback: CallbackQuery,
    session: AsyncSession,
    gateway: TelegramGateway,
) -> None:
    _, status, listing_id = callback.data.split(":")
    listing = await session.get(Listing, int(listing_id))
    if not listing:
        await callback.answer("Объявление не найдено", show_alert=True)
        return
    if callback.from_user.id != listing.owner_telegram_user_id:
        await callback.answer("Нет доступа", show_alert=True)
        return

    result = await apply_status_update(listing, RentStatus(status), gateway)
    if result.action == "archived":
        await log_event(
            session,
            event_type="listing_archived",
            user_id=listing.owner_telegram_user_id,
            listing_id=listing.id,
        )
    else:
        await log_event(
            session,
            event_type="listing_status_updated",
            user_id=listing.owner_telegram_user_id,
            listing_id=listing.id,
            metadata={"status": listing.rent_status.value},
        )

    await session.commit()
    await callback.answer("Готово")


@router.callback_query(F.data.startswith("bump:"))
async def bump_listing(
    callback: CallbackQuery,
    session: AsyncSession,
    gateway: TelegramGateway,
) -> None:
    _, listing_id = callback.data.split(":")
    listing = await session.get(Listing, int(listing_id))
    if not listing:
        await callback.answer("Объявление не найдено", show_alert=True)
        return
    if callback.from_user.id != listing.owner_telegram_user_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    now = datetime.now(timezone.utc)
    if not can_bump(listing, now):
        await callback.answer("Поднять можно раз в 24 часа", show_alert=True)
        return
    redis_client = redis.from_url(settings.redis_url)
    if await get_flag(redis_client, "pause_publications"):
        await redis_client.close()
        await callback.answer("Публикации на паузе", show_alert=True)
        return
    await redis_client.close()

    caption = build_caption(listing)
    message = await gateway.send_photo(
        chat_id=settings.public_channel_id,
        photo=listing.photo_file_id,
        caption=caption.text,
        reply_markup=caption.markup,
    )
    if listing.channel_message_id:
        await gateway.delete_message(
            chat_id=listing.channel_chat_id,
            message_id=listing.channel_message_id,
        )
    listing.channel_chat_id = settings.public_channel_id
    listing.channel_message_id = message.message_id
    listing.last_bump_at = now
    await session.commit()
    await log_event(
        session,
        event_type="listing_bumped_manual",
        user_id=listing.owner_telegram_user_id,
        listing_id=listing.id,
    )
    await callback.answer("Объявление поднято")


@router.callback_query(F.data.startswith("edit:"))
async def edit_listing(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    _, listing_id = callback.data.split(":")
    listing = await session.get(Listing, int(listing_id))
    if not listing:
        await callback.answer("Объявление не найдено", show_alert=True)
        return
    if callback.from_user.id != listing.owner_telegram_user_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(editing_listing_id=listing.id)
    await state.set_state(ListingForm.photo)
    await callback.message.answer("Отправьте новое фото для редактирования.")
    await callback.answer("Редактирование")


async def get_or_create_user(message: Message, session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.telegram_user_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.commit()
    return user

from __future__ import annotations

from base64 import b64decode
from datetime import datetime, timedelta, timezone

import sentry_sdk
from aiogram import Dispatcher
from aiogram.types import Update
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqladmin import Admin
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import EventAdmin, ListingAdmin, TemplateAdmin, UserAdmin
from app.config import settings
from app.db import SessionLocal, engine, get_session
from app.models import Event, Listing, ListingState, RentStatus, User
from app.telegram.bot_factory import create_bot
from app.telegram.gateway import TelegramGateway
from app.telegram.handlers import router

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)

app = FastAPI()
security = HTTPBasic()


def basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if (
        credentials.username != settings.admin_basic_user
        or credentials.password != settings.admin_basic_pass
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _is_basic_auth_valid(request: Request) -> bool:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return False
    try:
        decoded = b64decode(auth.split(" ", 1)[1]).decode()
        username, password = decoded.split(":", 1)
    except Exception:
        return False
    return username == settings.admin_basic_user and password == settings.admin_basic_pass


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        if not _is_basic_auth_valid(request):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized"},
                headers={"WWW-Authenticate": "Basic"},
            )
    return await call_next(request)


def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


dp = get_dispatcher()


@app.on_event("startup")
async def setup_admin() -> None:
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(ListingAdmin)
    admin.add_view(TemplateAdmin)
    admin.add_view(EventAdmin)


@app.post("/webhook")
async def webhook(request: Request) -> dict[str, str]:
    bot = create_bot()
    update = Update.model_validate(await request.json())
    async with SessionLocal() as session:
        async def session_provider():
            yield session

        gateway = TelegramGateway(bot=bot, session_provider=session_provider)
        await dp.feed_update(bot, update, session=session, gateway=gateway)
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard", dependencies=[Depends(basic_auth)])
async def dashboard(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    active_listings = await session.scalar(
        select(func.count()).where(Listing.state == ListingState.published)
    )
    free_listings = await session.scalar(
        select(func.count()).where(
            Listing.state == ListingState.published, Listing.rent_status == RentStatus.free
        )
    )
    booked_listings = await session.scalar(
        select(func.count()).where(
            Listing.state == ListingState.published, Listing.rent_status == RentStatus.booked
        )
    )
    pending_listings = await session.scalar(
        select(func.count()).where(Listing.state == ListingState.pending)
    )
    archived_today = await session.scalar(
        select(func.count()).where(
            Listing.state == ListingState.archived, Listing.updated_at >= day_ago
        )
    )
    users_total = await session.scalar(select(func.count()).select_from(User))
    users_24h = await session.scalar(
        select(func.count()).where(User.created_at >= day_ago)
    )
    users_7d = await session.scalar(
        select(func.count()).where(User.created_at >= week_ago)
    )
    errors_24h = await session.scalar(
        select(func.count()).where(Event.level == "error", Event.ts >= day_ago)
    )

    return {
        "active_listings": active_listings or 0,
        "free_listings": free_listings or 0,
        "booked_listings": booked_listings or 0,
        "pending_listings": pending_listings or 0,
        "archived_today": archived_today or 0,
        "users_total": users_total or 0,
        "users_24h": users_24h or 0,
        "users_7d": users_7d or 0,
        "errors_24h": errors_24h or 0,
    }

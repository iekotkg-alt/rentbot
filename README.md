# Rent Bot (Telegram)

Телеграм-бот для публикации объявлений о сдаче авто под такси в публичный канал с модерацией, админ-панелью и фоновой автоматикой.

## Возможности

- Подача объявления через бота с обязательными полями и фото.
- Модерация админами Telegram (/admin).
- Публикация в канал одним сообщением (фото + caption + inline-кнопки связи).
- Управление статусами и поднятиями через бота.
- Авто-удаление поста при статусе «Сдана».
- Напоминания владельцам активных объявлений.
- Веб-админка SQLAdmin + JSON dashboard.
- Celery + Redis + Postgres.
- Sentry для ошибок.

## Структура сервисов

- **Web**: FastAPI + aiogram webhook + SQLAdmin.
- **Worker**: Celery worker.
- **Beat**: Celery beat.
- **Postgres** и **Redis**.

## Переменные окружения

Смотрите `.env.example`.

## Локальный запуск (Docker Compose)

1. Создайте `.env` по примеру `.env.example`.
2. Запустите:

```bash
docker-compose up --build
```

3. Выполните миграции:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## Веб-админка

- SQLAdmin: `https://<host>/admin`
- Dashboard: `https://<host>/dashboard` (Basic Auth)

## Настройка webhook Telegram

После деплоя задайте вебхук:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://<your-domain>/webhook"
```

## Деплой на Render (рекомендуемый)

1. Создайте новый репозиторий на GitHub и запушьте этот проект.
2. В Render создайте:
   - **Postgres**
   - **Redis**
   - **Web Service** (Docker)
   - **Background Worker** (Celery worker)
   - **Background Worker** (Celery beat)
3. Для Web Service:
   - Build Command: `docker build -t rent-bot .`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Для Worker:
   - Start Command: `celery -A app.tasks worker -l info`
5. Для Beat:
   - Start Command: `celery -A app.tasks beat -l info`
6. Подключите переменные окружения из `.env.example`.
   - `DATABASE_URL` возьмите из Render Postgres, **в формате asyncpg**:
     `postgresql+asyncpg://...`
7. Включите HTTPS в Render (по умолчанию).
8. Установите webhook (см. выше).
9. Добавьте бота в канал с правами на публикацию и удаление сообщений.

## Тестирование

```bash
pytest --cov=app
```

## Лицензия

MIT

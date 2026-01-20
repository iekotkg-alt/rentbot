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

## Подробный деплой на Render (пошагово)

### Шаг 1. Подготовка Telegram
1. В BotFather создайте бота и получите `BOT_TOKEN`.
2. Создайте публичный канал для объявлений.
3. Добавьте бота в канал как администратора и дайте права:
   - `Post Messages`
   - `Delete Messages`
   - `Edit Messages`
4. Получите `PUBLIC_CHANNEL_ID` (например через @getidsbot или API).

### Шаг 2. GitHub
1. Создайте новый репозиторий на GitHub.
2. Запушьте код:
   ```bash
   git remote add origin <URL_ВАШЕГО_REPO>
   git push -u origin work
   ```

### Шаг 3. Создание сервисов в Render
1. Создайте **Postgres** (Render → New → PostgreSQL).
2. Создайте **Redis** (Render → New → Redis).
3. Создайте **Web Service** (Docker):
   - Repository: ваш GitHub репозиторий
   - Runtime: Docker
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Создайте **Background Worker** для Celery worker:
   - Start Command: `celery -A app.tasks worker -l info`
5. Создайте **Background Worker** для Celery beat:
   - Start Command: `celery -A app.tasks beat -l info`

### Шаг 4. Переменные окружения
В Render добавьте все переменные из `.env.example`, при этом:
- `DATABASE_URL` берите из Render Postgres, используйте формат:
  `postgresql+asyncpg://user:pass@host:port/dbname`
- `REDIS_URL` берите из Render Redis.
- `ADMIN_IDS` — список Telegram ID админов.
- `ADMIN_BASIC_USER` / `ADMIN_BASIC_PASS` — доступ к админке.

### Шаг 5. Миграции
Один раз выполните миграции:
1. Откройте Shell/Console в Web Service на Render.
2. Выполните:
   ```bash
   alembic revision --autogenerate -m "init"
   alembic upgrade head
   ```

### Шаг 6. Установка webhook
Когда Web Service запущен и есть домен (например `https://rent-bot.onrender.com`):
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://rent-bot.onrender.com/webhook"
```

### Шаг 7. Проверка
1. Откройте `https://<host>/health` → должно вернуть `{ "status": "ok" }`.
2. Откройте `https://<host>/admin` и авторизуйтесь.
3. Создайте объявление в боте и дождитесь публикации после модерации.

## Тестирование

```bash
pytest --cov=app
```

## Лицензия

MIT

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

## Деплой на VPS (dockhost.ru) — подробная инструкция

### Шаг 1. Подготовка Telegram
1. В BotFather создайте бота и получите `BOT_TOKEN`.
2. Создайте публичный канал для объявлений.
3. Добавьте бота в канал как администратора и дайте права:
   - `Post Messages`
   - `Delete Messages`
   - `Edit Messages`
4. Получите `PUBLIC_CHANNEL_ID` (например через @getidsbot или API).

### Шаг 2. Заказ VPS на dockhost.ru
1. Выберите минимальный тариф (достаточно для старта).
2. Укажите ОС Ubuntu 22.04.
3. Получите доступ по SSH (IP, логин, пароль/ключ).

### Шаг 3. Подключение к серверу и установка Docker
Подключитесь по SSH:

```bash
ssh root@<SERVER_IP>
```

Обновите систему и установите Docker + Compose:

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Проверьте, что Docker работает:

```bash
docker --version
docker compose version
```

### Шаг 4. Клонирование репозитория

```bash
apt install -y git
cd /opt

git clone https://github.com/iekotkg-alt/rentbot.git
cd rentbot
```

### Шаг 5. Настройка `.env`

Создайте `.env` на сервере:

```bash
cp .env.example .env
nano .env
```

Заполните переменные:
- `BOT_TOKEN`
- `PUBLIC_CHANNEL_ID`
- `ADMIN_IDS` (ID админов через запятую)
- `ADMIN_BASIC_USER` / `ADMIN_BASIC_PASS`
- `SENTRY_DSN` (если используете)

Остальные значения можно оставить как в примере.

### Шаг 6. Запуск контейнеров

```bash
docker compose up -d --build
```

Проверьте, что контейнеры запущены:

```bash
docker compose ps
```

### Шаг 7. Миграции базы данных

```bash
docker compose exec web alembic revision --autogenerate -m "init"
docker compose exec web alembic upgrade head
```

### Шаг 8. Настройка webhook

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://<YOUR_DOMAIN>/webhook"
```

Если домена пока нет, можно использовать IP и поднять SSL позже.

### Шаг 9. Настройка HTTPS (обязательно для webhook)

Telegram требует HTTPS. Рекомендуемый вариант — Nginx + бесплатный сертификат Let’s Encrypt.

1. Установите Nginx и Certbot:

```bash
apt install -y nginx certbot python3-certbot-nginx
```

2. Настройте виртуальный хост (пример `/etc/nginx/sites-available/rentbot`):

```nginx
server {
    listen 80;
    server_name <YOUR_DOMAIN>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфиг:

```bash
ln -s /etc/nginx/sites-available/rentbot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

3. Получите сертификат:

```bash
certbot --nginx -d <YOUR_DOMAIN>
```

После этого ваш webhook будет работать на HTTPS.

### Шаг 10. Проверка

1. Откройте `https://<YOUR_DOMAIN>/health` → должно вернуть `{ "status": "ok" }`.
2. Откройте `https://<YOUR_DOMAIN>/admin` и авторизуйтесь.
3. Создайте объявление в боте и дождитесь публикации после модерации.

## Тестирование

```bash
pytest --cov=app
```

## Лицензия

MIT

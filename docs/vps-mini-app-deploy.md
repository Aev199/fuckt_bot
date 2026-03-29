# VPS Deploy Guide For Mini App

## Important

Telegram Mini App должен открываться по HTTPS. Обычный `http://IP:8000/app` внутри Telegram работать не будет.

Нужны:

- домен
- nginx reverse proxy
- TLS-сертификат

## Minimal Flow

1. Клонировать проект на сервер
2. Создать `.venv`
3. Установить зависимости
4. Заполнить `.env`
5. Применить `alembic upgrade head`
6. Поднять backend через `systemd`
7. Поднять bot через `systemd`
8. Настроить nginx
9. Выпустить сертификат через certbot

## Required .env values

```env
BOT_TOKEN=...
DATABASE_URL=sqlite+aiosqlite:///./knowledge_base.db
ADMIN_ID=...
MINI_APP_URL=https://kb.example.com/app
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=["https://kb.example.com"]
```

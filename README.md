# Geotech Knowledge Base Mini App

Telegram Mini App для личной базы знаний по геотехнике.

## Что уже есть

- FastAPI backend
- Telegram WebApp auth через `initData`
- CRUD для категорий и материалов
- поиск по заголовку, тексту, заметкам и источнику
- избранное
- редактирование и удаление материалов прямо в Mini App
- aiogram launcher-бот
- Alembic-миграция для новой схемы `kb_*`

## Основные файлы

- [docs/mini-app-mvp-spec.md](docs/mini-app-mvp-spec.md)
- [docs/mini-app-roadmap.md](docs/mini-app-roadmap.md)
- [docs/vps-mini-app-deploy.md](docs/vps-mini-app-deploy.md)
- [app/backend/main.py](app/backend/main.py)
- [app/bot/main.py](app/bot/main.py)
- [app/frontend/index.html](app/frontend/index.html)

## Локальный запуск

1. Создай и активируй окружение:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

2. Установи зависимости:

```bash
python -m pip install -r requirements.txt
```

3. Создай `.env` из примера и заполни:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Минимум:

- `BOT_TOKEN`
- `ADMIN_ID`
- `MINI_APP_URL`

Локальный пример:

```env
DATABASE_URL=sqlite+aiosqlite:///./knowledge_base.db
MINI_APP_URL=http://127.0.0.1:8000/app
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=["*"]
```

4. Примени миграции:

```bash
python -m alembic upgrade head
```

5. Запусти backend:

```bash
uvicorn run_backend:app --host 127.0.0.1 --port 8000 --reload
```

6. Запусти Telegram-бота:

```bash
python -m app.bot.main
```

После этого:

- API health: `http://127.0.0.1:8000/health`
- Mini App: `http://127.0.0.1:8000/app`

## API

- `POST /api/auth/telegram`
- `GET /api/categories`
- `POST /api/categories`
- `GET /api/materials`
- `POST /api/materials`
- `GET /api/materials/{id}`
- `PATCH /api/materials/{id}`
- `DELETE /api/materials/{id}`
- `POST /api/materials/{id}/favorite`
- `GET /api/search`

## Deploy templates

- [deploy/systemd/geotech-kb-backend.service](deploy/systemd/geotech-kb-backend.service)
- [deploy/systemd/geotech-kb-bot.service](deploy/systemd/geotech-kb-bot.service)
- [deploy/nginx/geotech-kb.conf](deploy/nginx/geotech-kb.conf)

## Что дальше логично делать

- перейти с `LIKE` на SQLite FTS5
- вынести frontend на React/Vite
- добавить вложения и файлы
- добавить import по URL с парсингом статьи

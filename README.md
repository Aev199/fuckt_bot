# Geotech Knowledge Bot + Web Cabinet

Личная база знаний по геотехнике в формате:

- основной интерфейс: Telegram-бот с pseudo-SPA навигацией через inline-кнопки
- вспомогательный интерфейс: web-кабинет для спокойного редактирования и работы с длинными текстами

## Что уже есть

- FastAPI backend
- aiogram 3 bot
- SQLite + SQLAlchemy 2.0 async
- Alembic migrations
- категории, материалы, теги, избранное
- фото-вложения к материалам
- поиск по заголовку, тексту, заметкам и источнику
- web-кабинет для редактирования материалов

## Основные файлы

- [docs/spa-bot-web-spec.md](docs/spa-bot-web-spec.md)
- [app/backend/main.py](app/backend/main.py)
- [app/backend/db/models.py](app/backend/db/models.py)
- [app/bot/main.py](app/bot/main.py)
- [app/bot/handlers/knowledge.py](app/bot/handlers/knowledge.py)
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

3. Создай `.env` из примера:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Минимально заполни:

- `BOT_TOKEN`
- `ADMIN_ID`
- `MINI_APP_URL`
- `WEB_CABINET_TOKEN`

Пример для локальной разработки:

```env
DATABASE_URL=sqlite+aiosqlite:///./knowledge_base.db
MINI_APP_URL=http://127.0.0.1:8000/app
WEB_CABINET_TOKEN=change_me_for_browser_access
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
python -m uvicorn run_backend:app --host 127.0.0.1 --port 8000 --reload
```

6. Запусти бота:

```bash
python -m app.bot.main
```

После этого:

- API: `http://127.0.0.1:8000/health`
- web-кабинет: `http://127.0.0.1:8000/app?token=YOUR_TOKEN`

## Команды бота

- `/start` или `/menu` — главное меню
- `/add` — быстрое добавление материала
- `/search` — поиск материалов
- `/web` — ссылка на web-кабинет
- `/help` — помощь

Чтобы прикрепить фото:

1. открой материал в боте
2. нажми `Добавить фото`
3. отправь фотографию одним сообщением

После этого фото появится и в карточке материала, и в web-кабинете.

## Как устроен web-кабинет

- если кабинет открыт из Telegram Mini App, используется Telegram auth
- если кабинет открыт как обычный сайт, используется `WEB_CABINET_TOKEN`
- из карточки материала в боте можно открыть сразу нужный материал в web через параметр `material_id`

## Deploy templates

- [deploy/systemd/geotech-kb-backend.service](deploy/systemd/geotech-kb-backend.service)
- [deploy/systemd/geotech-kb-bot.service](deploy/systemd/geotech-kb-bot.service)
- [deploy/nginx/geotech-kb.conf](deploy/nginx/geotech-kb.conf)

## Следующие разумные шаги

- полнотекстовый поиск через SQLite FTS5
- редактирование материала прямо в Telegram-боте
- импорт материалов из ссылки или пересланного сообщения
- вложения и файлы

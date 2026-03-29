# Geotech Knowledge Base Mini App MVP

## Product Goal

Сделать Telegram Mini App для личной базы знаний по геотехнике.

MVP должен решать две ключевые задачи:

1. Быстро сохранять полезные материалы, чтобы не потерять найденную информацию.
2. Быстро находить уже сохранённые материалы через категории и поиск.

## Core Use Cases

### 1. Сохранение материала

- пользователь нашёл полезную информацию
- открыл Mini App
- добавил материал вручную
- указал категорию, источник и заметки
- сохранил в БД

### 2. Доступ к справочнику

- пользователь открыл Mini App
- ищет материал по категории, заголовку, тексту, тегам или источнику
- открывает карточку материала

## MVP Scope

### Material management

- добавить материал вручную
- сохранить заголовок
- сохранить основной текст
- сохранить ссылку на источник
- сохранить имя источника
- сохранить дополнительные заметки
- выбрать категорию
- добавить теги
- редактировать материал
- удалить материал
- отметить материал как избранный

### Knowledge directory

- список категорий
- список материалов
- фильтрация по категории
- поиск по заголовку, тексту, заметкам и источнику
- просмотр полной карточки материала

### Telegram integration

- запуск Mini App через Telegram-бота
- аутентификация через Telegram WebApp init data
- без отдельной регистрации и логина

## Suggested Stack

- Telegram bot: aiogram 3.x
- Backend API: FastAPI
- Database: SQLite for MVP
- ORM: SQLAlchemy 2.0 async
- Migrations: Alembic
- Mini App frontend: lightweight web UI
- Search: SQL LIKE search for first iteration, later FTS5

## Data Model

### User

- id
- telegram_id
- username
- created_at

### Category

- id
- user_id
- name
- slug
- parent_id nullable
- created_at

### Material

- id
- user_id
- category_id nullable
- title
- content
- source_url nullable
- source_name nullable
- notes nullable
- is_favorite
- created_at
- updated_at

### Tag

- id
- user_id
- name
- slug

### MaterialTag

- id
- material_id
- tag_id

## Main Screens

- Home
- Add Material
- Materials
- Material Detail
- Categories

## API Endpoints

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

## Bot Responsibilities

Бот теперь нужен только как launcher:

- `/start`
- приветствие
- кнопка `Открыть базу знаний`
- кнопка `Добавить материал`

## Out of Scope For First MVP

- AI-summary
- автопарсинг ссылок
- генерация карточек
- напоминания
- полнотекстовый поиск по PDF
- вложения и файлы

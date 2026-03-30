# Geotech Knowledge Bot + Web Cabinet

## Product Format

Основной интерфейс продукта — Telegram bot в формате pseudo-SPA.

Дополнительный интерфейс — web cabinet для спокойного редактирования и структурирования материалов.

## Main UX Principles

### Telegram bot is primary

Бот должен быть главным способом:

- быстро сохранить материал
- найти материал
- открыть материал
- пройти по категориям
- посмотреть избранное
- посмотреть последние материалы

### Web is secondary

Web нужен как вспомогательный кабинет:

- длинное редактирование
- просмотр большого объёма контента
- чистка структуры
- более удобная работа с текстами

## Bot Sections

- Главная
- Добавить материал
- Поиск
- Категории
- Последние
- Избранное
- Карточка материала
- Открыть web-кабинет

## Bot Interaction Model

- навигация через `InlineKeyboard`
- ключевые экраны редактируются через `edit_message_text`
- ввод данных делается через FSM и обычные сообщения
- после завершения FSM бот возвращает пользователя в основной интерфейс

## Material Add Flow

1. title
2. content
3. source_url optional
4. source_name optional
5. notes optional
6. category selection
7. tags
8. save and show material card

## Search Flow

1. пользователь нажимает `Поиск`
2. бот просит отправить запрос
3. пользователь отправляет текст
4. бот показывает результаты кнопками

## Data Model

Используется knowledge-base схема:

- `kb_users`
- `kb_categories`
- `kb_materials`
- `kb_tags`
- `kb_material_tags`

## Command Set

- `/start`
- `/menu`
- `/add`
- `/search`
- `/web`
- `/help`

## Web Cabinet Responsibilities

- список материалов
- редактирование материалов
- удаление
- поиск
- фильтры
- работа с категориями

## Deployment Shape

На сервере работают два процесса:

1. FastAPI backend
2. Telegram bot

Web cabinet раздаётся backend'ом.

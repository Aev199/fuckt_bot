# Geotech Flashcards Bot

Telegram-бот для обучения по карточкам по геотехнике.

## Что умеет

- запускать учебные сессии по 5 карточек
- выбирать тему или проходить все темы
- показывать ответ через `edit_message_text`
- сохранять результат по каждой карточке
- отправлять ежедневные напоминания через APScheduler
- загружать карточки из `cards.json`

## Стек

- Python 3.11+
- aiogram 3.x
- SQLAlchemy 2.0 async
- SQLite + aiosqlite
- Alembic
- APScheduler
- pydantic-settings

## Структура

```text
bot/
  handlers/
  keyboards.py
  middlewares.py
  states.py
data/
  load_cards.py
db/
  crud.py
  database.py
  models.py
migrations/
scheduler/
  reminders.py
.env.example
alembic.ini
cards.json
config.py
main.py
requirements.txt
```

## Локальный запуск

1. Создай виртуальное окружение:

```bash
python -m venv .venv
```

2. Активируй его.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

3. Установи зависимости:

```bash
python -m pip install -r requirements.txt
```

4. Создай `.env` из шаблона:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

5. Заполни в `.env`:

- `BOT_TOKEN`
- `ADMIN_ID`

6. Примени миграции:

```bash
python -m alembic upgrade head
```

7. Загрузи карточки:

```bash
python data/load_cards.py
```

8. Запусти бота:

```bash
python main.py
```

## Как редактировать карточки

Правильный способ:

1. Редактируй `cards.json`
2. Не меняй `id` у существующих карточек
3. Для новой карточки добавляй новый уникальный `id`
4. После изменений запускай:

```bash
python data/load_cards.py
```

Теперь загрузчик умеет:

- добавлять новые карточки
- обновлять существующие карточки по `id`
- сохранять вопрос, ответ, hint, topic, difficulty и другие поля в актуальном виде

Важно:

- `id` в `cards.json` теперь является стабильным идентификатором карточки
- если хочешь “удалить” карточку, лучше поставить `"active": false`, чем убирать её из базы вручную

## Подготовка к GitHub

Перед публикацией:

- убедись, что в репозиторий не попадает `.env`
- не коммить `bot.db`
- не коммить локальные исходники вроде `book.pdf`, `facts.db`, `images/`
- проверь, что токен бота не светился в истории git

Если токен уже попадал в коммиты или в открытый файл, его нужно перевыпустить через BotFather.

## Деплой на VPS

Ниже пример для Ubuntu.

### 1. Установить системные пакеты

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 2. Клонировать проект

```bash
cd /opt
sudo git clone <YOUR_GITHUB_REPO_URL> geotech-flashcards-bot
sudo chown -R $USER:$USER /opt/geotech-flashcards-bot
cd /opt/geotech-flashcards-bot
```

### 3. Настроить окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

После этого заполни `.env`.

### 4. Инициализировать базу

```bash
python -m alembic upgrade head
python data/load_cards.py
```

### 5. Проверить ручной запуск

```bash
python main.py
```

Если бот стартует нормально, останови его и подключи systemd.

### 6. Подключить systemd

Готовый файл лежит в [deploy/systemd/geotech-flashcards-bot.service](deploy/systemd/geotech-flashcards-bot.service).

Установка:

```bash
sudo cp deploy/systemd/geotech-flashcards-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable geotech-flashcards-bot
sudo systemctl start geotech-flashcards-bot
```

Проверка:

```bash
sudo systemctl status geotech-flashcards-bot
sudo journalctl -u geotech-flashcards-bot -f
```

## Обновление на сервере

```bash
cd /opt/geotech-flashcards-bot
git pull
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
sudo systemctl restart geotech-flashcards-bot
```

Если менялся `cards.json`:

```bash
python data/load_cards.py
sudo systemctl restart geotech-flashcards-bot
```

# Mini App Roadmap

## Phase 1. Foundation

- save the new product spec
- scaffold backend, bot launcher and web UI
- add config values for backend and Mini App URL

## Phase 2. Backend

- implement async SQLAlchemy models
- implement Telegram WebApp auth validation
- implement CRUD for categories
- implement CRUD for materials
- implement search endpoint

## Phase 3. Mini App

- add simple single-page web UI
- auth through Telegram WebApp init data
- categories list and create form
- material create form
- materials list with search and filters
- favorite toggle

## Phase 4. Telegram Bot

- simplify bot into launcher
- `/start` with WebApp buttons
- separate Python entrypoint for bot polling

## Phase 5. Ops

- update README
- update dependencies
- add run instructions for backend and bot
- later add systemd units for both processes

from aiogram.fsm.state import State, StatesGroup


class AddMaterialStates(StatesGroup):
    title = State()
    content = State()
    source_url = State()
    source_name = State()
    notes = State()
    category = State()
    tags = State()


class SearchStates(StatesGroup):
    waiting_query = State()


class CategoryStates(StatesGroup):
    creating_name = State()


class AttachmentStates(StatesGroup):
    waiting_photo = State()

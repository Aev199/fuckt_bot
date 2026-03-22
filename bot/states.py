from aiogram.fsm.state import State, StatesGroup


class SessionStates(StatesGroup):
    choosing_topic = State()
    in_session = State()
    answer_shown = State()
    session_done = State()


class NotificationStates(StatesGroup):
    choosing_timezone = State()
    choosing_time = State()

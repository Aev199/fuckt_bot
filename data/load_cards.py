from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from db.database import async_session_factory
from db.models import Card


logger = logging.getLogger(__name__)


def _resolve_cards_path() -> Path:
    cards_path = Path(settings.cards_json_path)
    if not cards_path.is_absolute():
        cards_path = PROJECT_ROOT / cards_path
    return cards_path


def _load_cards_from_json(cards_path: Path) -> list[dict]:
    with cards_path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError("cards.json must contain a JSON array of card objects.")

    return payload


def _validate_card(raw_card: dict, index: int) -> dict:
    required_fields = ("card_type", "topic", "difficulty", "question", "answer")
    missing_fields = [field for field in required_fields if field not in raw_card or raw_card[field] in (None, "")]
    if missing_fields:
        raise ValueError(f"Card #{index} is missing required fields: {', '.join(missing_fields)}")

    card_type = str(raw_card["card_type"]).strip()
    if card_type not in {"recall", "quiz"}:
        raise ValueError(f"Card #{index} has invalid card_type: {card_type}")

    difficulty = int(raw_card["difficulty"])
    if difficulty not in {1, 2, 3}:
        raise ValueError(f"Card #{index} has invalid difficulty: {difficulty}")

    question = str(raw_card["question"]).strip()
    answer = str(raw_card["answer"]).strip()

    card = {
        "card_type": card_type,
        "topic": str(raw_card["topic"]).strip(),
        "subtopic": str(raw_card["subtopic"]).strip() if raw_card.get("subtopic") else None,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "hint": str(raw_card["hint"]).strip() if raw_card.get("hint") else None,
        "active": bool(raw_card.get("active", True)),
        "options": None,
        "answer_index": None,
    }

    if card_type == "quiz":
        options = raw_card.get("options")
        answer_index = raw_card.get("answer_index")

        if not isinstance(options, list) or not options:
            raise ValueError(f"Card #{index} with card_type=quiz must contain a non-empty options list.")
        if answer_index is None:
            raise ValueError(f"Card #{index} with card_type=quiz must contain answer_index.")

        normalized_options = [str(option).strip() for option in options]
        answer_index = int(answer_index)

        if answer_index < 0 or answer_index >= len(normalized_options):
            raise ValueError(f"Card #{index} has answer_index outside options range.")

        card["options"] = normalized_options
        card["answer_index"] = answer_index

    return card


def _ensure_no_source_duplicates(cards: list[dict]) -> list[dict]:
    seen_questions: set[str] = set()
    duplicates: list[str] = []
    validated_cards: list[dict] = []

    for index, raw_card in enumerate(cards, start=1):
        card = _validate_card(raw_card=raw_card, index=index)
        normalized_question = card["question"]

        if normalized_question in seen_questions:
            duplicates.append(normalized_question)
            continue

        seen_questions.add(normalized_question)
        validated_cards.append(card)

    if duplicates:
        duplicate_lines = "\n".join(f"- {question}" for question in duplicates)
        raise ValueError(f"Duplicate questions found in JSON source:\n{duplicate_lines}")

    return validated_cards


async def load_cards() -> None:
    cards_path = _resolve_cards_path()
    if not cards_path.exists():
        raise FileNotFoundError(f"Cards file not found: {cards_path}")

    raw_cards = _load_cards_from_json(cards_path)
    prepared_cards = _ensure_no_source_duplicates(raw_cards)

    questions = [card["question"] for card in prepared_cards]

    async with async_session_factory() as session:
        existing_questions_result = await session.execute(
            select(Card.question).where(Card.question.in_(questions))
        )
        existing_questions = set(existing_questions_result.scalars().all())

        new_cards = [
            Card(**card_data)
            for card_data in prepared_cards
            if card_data["question"] not in existing_questions
        ]

        if not new_cards:
            logger.info("No new cards found. Database is already up to date.")
            return

        session.add_all(new_cards)
        await session.commit()

        logger.info(
            "Cards import completed: total_in_file=%s, already_in_db=%s, inserted=%s",
            len(prepared_cards),
            len(existing_questions),
            len(new_cards),
        )


async def main() -> None:
    await load_cards()


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    try:
        asyncio.run(main())
    except Exception:
        logger.exception("Failed to load cards into the database.")
        raise

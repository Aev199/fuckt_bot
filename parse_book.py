import re
import os
import sqlite3
import fitz


IMAGES_DIR = "images"

QUESTION_START_RE = re.compile(r'М\.\d+\.\d+\.\s+.*?\?')
QUESTION_ID_RE = re.compile(r'^М\.(\d+\.\d+)\.\s*(.*)$')
FIGURE_TEXT_RE = re.compile(r'Рис\.\s*М?\.(\d+\.\d+)')


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_question(text: str):
    m = QUESTION_ID_RE.match(text)
    if not m:
        return None, text.strip()
    return f"M.{m.group(1)}", m.group(2).strip()


def clean_answer(text: str) -> str:
    text = re.split(r'\bРис\.', text)[0]
    return text.strip()


def find_figure_caption_blocks(page):
    """
    Возвращает список найденных подписей рисунков на странице:
    [
      {"figure_id": "M.2.14", "rect": fitz.Rect(...)},
      ...
    ]
    """
    blocks = page.get_text("blocks")
    captions = []

    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        if not text:
            continue

        normalized = normalize_text(text)
        m = FIGURE_TEXT_RE.search(normalized)
        if m:
            captions.append({
                "figure_id": f"M.{m.group(1)}",
                "rect": fitz.Rect(x0, y0, x1, y1),
                "text": normalized,
            })

    captions.sort(key=lambda c: c["rect"].y0)
    return captions


def render_figure_from_caption(page, page_index: int, caption: dict) -> str:
    """
    Вырезает область рисунка НАД подписью.
    """
    page_rect = page.rect
    cap = caption["rect"]

    # Отступы можно подстроить под книгу
    side_margin = 12
    bottom_gap = 6

    # Базовая эвристика:
    # рисунок начинается заметно выше подписи
    # для учебников часто работает 35–50% высоты страницы выше подписи
    estimated_top = max(page_rect.y0, cap.y0 - page_rect.height * 0.38)

    clip = fitz.Rect(
        page_rect.x0 + side_margin,
        estimated_top,
        page_rect.x1 - side_margin,
        cap.y0 - bottom_gap
    )

    # защита от кривых координат
    if clip.height < 40:
        clip = fitz.Rect(
            page_rect.x0 + side_margin,
            max(page_rect.y0, cap.y0 - page_rect.height * 0.45),
            page_rect.x1 - side_margin,
            cap.y0 - bottom_gap
        )

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip, alpha=False)

    filename = f"{caption['figure_id']}_page_{page_index + 1}.png"
    path = os.path.join(IMAGES_DIR, filename)
    pix.save(path)

    return path


def parse_pdf(pdf_path: str):
    os.makedirs(IMAGES_DIR, exist_ok=True)

    doc = fitz.open(pdf_path)
    facts = []
    current_fact = None

    for page_index in range(len(doc)):
        page = doc[page_index]
        raw_text = page.get_text("text")
        text = normalize_text(raw_text)

        if not text:
            continue

        question_matches = list(QUESTION_START_RE.finditer(text))
        figure_captions = find_figure_caption_blocks(page)

        # если на странице есть подписи рисунков, рендерим их
        rendered_figures = []
        for cap in figure_captions:
            try:
                img_path = render_figure_from_caption(page, page_index, cap)
                rendered_figures.append({
                    "figure_id": cap["figure_id"],
                    "image_path": img_path,
                    "caption_rect": cap["rect"],
                })
            except Exception as e:
                print(f"[WARN] Не удалось сохранить рисунок {cap['figure_id']} на странице {page_index + 1}: {e}")

        # если вопросов нет, это продолжение предыдущего ответа
        if not question_matches:
            if current_fact:
                current_fact["answer"] += " " + text
                if rendered_figures and current_fact["image"] is None:
                    current_fact["image"] = rendered_figures[0]["image_path"]
            continue

        page_facts = []

        for i, match in enumerate(question_matches):
            start = match.start()
            end = question_matches[i + 1].start() if i + 1 < len(question_matches) else len(text)
            block = text[start:end].strip()

            q_raw = match.group(0)
            answer_raw = block[len(q_raw):].strip()

            qid, question = parse_question(q_raw)
            answer = clean_answer(answer_raw)

            fact = {
                "id": qid,
                "question": question,
                "answer": answer,
                "page": page_index + 1,
                "image": None
            }

            facts.append(fact)
            page_facts.append(fact)
            current_fact = fact

        # простая привязка:
        # если на странице один вопрос и один рисунок — связываем их
        if len(page_facts) == 1 and len(rendered_figures) == 1:
            page_facts[0]["image"] = rendered_figures[0]["image_path"]

        # если на странице несколько вопросов, а рисунок один —
        # обычно он относится к последнему блоку перед подписью / к ближайшему контексту.
        elif page_facts and rendered_figures:
            page_facts[-1]["image"] = rendered_figures[0]["image_path"]

    for f in facts:
        f["answer"] = re.sub(r'\s+', ' ', f["answer"]).strip()

    facts = [f for f in facts if f["id"] and len(f["answer"]) > 20]
    return facts


def init_db(db_path="facts.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS facts (
        id TEXT PRIMARY KEY,
        question TEXT,
        answer TEXT,
        page INTEGER,
        image_path TEXT
    )
    """)

    conn.commit()
    return conn


def insert_facts(conn, facts):
    cur = conn.cursor()

    for f in facts:
        cur.execute("""
        INSERT OR REPLACE INTO facts (id, question, answer, page, image_path)
        VALUES (?, ?, ?, ?, ?)
        """, (
            f["id"],
            f["question"],
            f["answer"],
            f["page"],
            f["image"]
        ))

    conn.commit()


if __name__ == "__main__":
    PDF_PATH = "book.pdf"

    print("Парсим PDF...")
    facts = parse_pdf(PDF_PATH)
    print(f"Извлечено фактов: {len(facts)}")

    conn = init_db("facts.db")
    insert_facts(conn, facts)

    print("Готово: facts.db и images/")
"""
extract_questions.py
PDF (scan) -> pix2text OCR -> regex parser -> questions.json
"""
import json
import re
import fitz
from pathlib import Path
from PIL import Image
from pix2text import Pix2Text
from pix2text.layout_parser import ElementType

# ── Config ───────────────────────────────────────────────────────────────────
PDF_PATH  = 'input/de-toan.pdf'
OUT_DIR   = Path('output')
IMG_DIR   = OUT_DIR / 'pages'
OUT_JSON  = OUT_DIR / 'questions.json'
TEST_MODE = True   # True = first page only; set False for full run

for d in (OUT_DIR, IMG_DIR):
    d.mkdir(exist_ok=True)

# ── Regex patterns ───────────────────────────────────────────────────────────
# Section headers — broad patterns to survive imperfect OCR
SECTION_RE = [
    (1, re.compile(r'PH[^\s]*N\s+I\b|TR[^\s]*C\s+NGHI[^\s]*M', re.I)),
    (2, re.compile(r'PH[^\s]*N\s+II\b|[DĐ][^\s]*NG[/\s]+SAI', re.I)),
    (3, re.compile(r'PH[^\s]*N\s+III\b|TR[^\s]*\s+L[^\s]*I\s+NG[^\s]*N', re.I)),
]

# Question boundary: "Câu N." or "Câu N:" (also handles OCR variants C[aâ]u)
QUESTION_SPLIT = re.compile(r'(?=C[aâA]u\s+\d+\s*[.:])', re.I)

# Question header: capture number + rest of body
QUESTION_HDR = re.compile(r'C[aâA]u\s+(\d+)\s*[.:]?\s*(.*)', re.S | re.I)

# A/B/C/D options for multiple_choice
OPTIONS_RE = re.compile(
    r'\bA[.\)]\s*(.*?)\s*\bB[.\)]\s*(.*?)\s*\bC[.\)]\s*(.*?)\s*\bD[.\)]\s*(.*?)$',
    re.S,
)

# a/b/c/d sub-items for true_false
SUBITEM_RE = re.compile(r'\b([a-d])[.\)]\s*(.*?)(?=\n\s*[a-d][.\)]|\Z)', re.S)


# ── PDF page -> JPEG ──────────────────────────────────────────────────────────
def page_to_jpg(doc: fitz.Document, page_idx: int, dpi: int = 200) -> Path:
    page = doc[page_idx]
    mat  = fitz.Matrix(dpi / 72, dpi / 72)
    pix  = page.get_pixmap(matrix=mat)
    png_path = IMG_DIR / f"page_{page_idx + 1}.png"
    jpg_path = IMG_DIR / f"page_{page_idx + 1}.jpg"
    pix.save(str(png_path))
    img = Image.open(png_path).convert('RGB')
    img.save(str(jpg_path), 'JPEG', quality=85)
    print(f"   {img.size[0]}x{img.size[1]}px — {jpg_path.stat().st_size // 1024} KB")
    return jpg_path


# ── OCR one page ──────────────────────────────────────────────────────────────
def ocr_page(p2t: Pix2Text, jpg_path: Path) -> dict:
    """Run pix2text on a page image; return structured OCR data."""
    page_result = p2t.recognize_page(str(jpg_path))

    text_blocks   = []   # {'text': str, 'ymin': float, 'ymax': float}
    tables        = []   # markdown strings
    figure_yranges = []  # (ymin, ymax) of figure elements

    for elem in page_result.elements:
        ymin = float(elem.box[1])
        ymax = float(elem.box[3])

        if elem.type in (ElementType.TEXT, ElementType.TITLE, ElementType.PLAIN_TEXT):
            text_blocks.append({'text': elem.text, 'ymin': ymin, 'ymax': ymax, 'kind': 'text'})
        elif elem.type == ElementType.FORMULA:
            text_blocks.append({'text': elem.text, 'ymin': ymin, 'ymax': ymax, 'kind': 'formula'})
        elif elem.type == ElementType.TABLE:
            tables.append(elem.text)
            text_blocks.append({'text': '[TABLE]', 'ymin': ymin, 'ymax': ymax, 'kind': 'table'})
        elif elem.type == ElementType.FIGURE:
            figure_yranges.append((ymin, ymax))
            text_blocks.append({'text': '[FIGURE]', 'ymin': ymin, 'ymax': ymax, 'kind': 'figure'})

    text_blocks.sort(key=lambda b: b['ymin'])

    full_text = '\n'.join(b['text'] for b in text_blocks)

    return {
        'full_text': full_text,
        'tables': tables,
        'figure_yranges': figure_yranges,
    }


# ── Parse questions from one page's OCR text ─────────────────────────────────
def parse_questions(page_data: dict, current_section: int, id_start: int, page_num: int):
    """Return (questions_list, updated_section)."""
    full_text = page_data['full_text']
    tables    = page_data['tables']

    # Update section if a section header appears anywhere on this page
    for sec_id, pat in SECTION_RE:
        if pat.search(full_text):
            current_section = sec_id
            break

    # Split text into per-question chunks
    chunks = QUESTION_SPLIT.split(full_text)

    questions  = []
    id_counter = id_start
    table_idx  = 0

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Section header can appear inside a chunk when page has multiple sections
        for sec_id, pat in SECTION_RE:
            if pat.search(chunk):
                current_section = sec_id

        m = QUESTION_HDR.match(chunk)
        if not m:
            continue

        body = m.group(2).strip()

        has_table  = '[TABLE]' in chunk
        has_figure = '[FIGURE]' in chunk

        # Assign next unused table's markdown
        table_md = None
        if has_table and table_idx < len(tables):
            table_md  = tables[table_idx]
            table_idx += 1

        opt_m  = OPTIONS_RE.search(body)
        subs   = SUBITEM_RE.findall(body)

        if opt_m and current_section == 1:
            # Remove option lines from question_text
            q_text = body[:opt_m.start()].strip()
            q = {
                'id': id_counter,
                'section': 1,
                'type': 'multiple_choice',
                'question_text': q_text,
                'options': {
                    'A': opt_m.group(1).strip(),
                    'B': opt_m.group(2).strip(),
                    'C': opt_m.group(3).strip(),
                    'D': opt_m.group(4).strip(),
                },
                'correct_answer': None,
                'has_figure': has_figure,
                'figure_path': None,
                'has_table': has_table,
                'table_markdown': table_md,
                'page': page_num,
                'points': 0.25,
            }

        elif len(subs) >= 4 and current_section == 2:
            # Find where sub-items start
            first_sub = SUBITEM_RE.search(body)
            q_text = body[:first_sub.start()].strip() if first_sub else body
            q = {
                'id': id_counter,
                'section': 2,
                'type': 'true_false',
                'question_text': q_text,
                'sub_items': [
                    {'label': label, 'statement': stmt.strip(), 'is_correct': None}
                    for label, stmt in subs[:4]
                ],
                'has_figure': has_figure,
                'figure_path': None,
                'has_table': has_table,
                'table_markdown': table_md,
                'page': page_num,
            }

        else:
            q = {
                'id': id_counter,
                'section': current_section,
                'type': 'short_answer',
                'question_text': body.strip(),
                'answer': None,
                'has_figure': has_figure,
                'figure_path': None,
                'has_table': has_table,
                'table_markdown': table_md,
                'page': page_num,
                'points': 0.5,
            }

        questions.append(q)
        id_counter += 1

    return questions, current_section


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"PDF: {total_pages} trang\n")

    print("Khoi tao pix2text (lan dau se tai models ~500 MB)...")
    p2t = Pix2Text.from_config()
    print("OK\n")

    all_questions   = []
    current_section = 1
    id_counter      = 1
    pages_to_run    = 1 if TEST_MODE else total_pages

    for i in range(pages_to_run):
        page_num = i + 1
        print(f"Trang {page_num}/{total_pages}...")

        jpg_path  = page_to_jpg(doc, i, dpi=200)
        page_data = ocr_page(p2t, jpg_path)

        print(f"   OCR: {len(page_data['full_text'])} chars, "
              f"{len(page_data['tables'])} tables, "
              f"{len(page_data['figure_yranges'])} figures")

        questions, current_section = parse_questions(
            page_data, current_section, id_counter, page_num
        )
        id_counter      += len(questions)
        all_questions.extend(questions)

        print(f"   {len(questions)} cau hoi (section {current_section})\n")

    result = {
        'exam_info': {
            'title': 'De Toan',
            'total_questions': len(all_questions),
            'sections': [
                {'id': 1, 'name': 'Trac nghiem', 'count': 12, 'points_each': 0.25},
                {'id': 2, 'name': 'Dung/Sai',    'count': 4,
                 'scoring': {'1_correct': 0.1, '2_correct': 0.25, '3_correct': 0.5, '4_correct': 1.0}},
                {'id': 3, 'name': 'Tra loi ngan', 'count': 6, 'points_each': 0.5},
            ],
        },
        'questions': all_questions,
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Saved {len(all_questions)} cau -> {OUT_JSON}")


if __name__ == '__main__':
    main()

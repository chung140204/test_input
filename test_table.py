# test_table.py — Test TABLE detection dùng PyMuPDF
import fitz
from pathlib import Path

OUT_DIR = Path('output/tables')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (tên, trang, y_start, y_end) — pixel coords tại 200 DPI
CASES = [
    ('cau3_bang_tan_so', 'input/page_1.png', 880, 1360),
]

SCALE = 72 / 200  # 200-DPI pixels → PDF points

def page_idx(page_path):
    return int(Path(page_path).stem.split('_')[1]) - 1

def main():
    doc = fitz.open('input/de-toan.pdf')
    summary = []

    for name, page_path, y0, y1 in CASES:
        page = doc[page_idx(page_path)]
        W = page.rect.width
        clip = fitz.Rect(0, y0 * SCALE, W, y1 * SCALE)

        # Lưu crop để kiểm tra bằng mắt
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        pix.save(str(OUT_DIR / f"{name}_crop.png"))

        # Detect bảng trong vùng này
        tabs = page.find_tables(clip=clip)
        tables = tabs.tables if tabs else []

        print(f"{'='*55}")
        print(f"  {name}")
        print(f"{'='*55}")
        print(f"  Crop saved  : output/tables/{name}_crop.png")
        print(f"  Tables found: {len(tables)}")

        for i, tbl in enumerate(tables):
            df = tbl.to_pandas()
            txt = df.to_markdown(index=False)

            txt_file = OUT_DIR / f"{name}_table_{i}.txt"
            txt_file.write_text(txt, encoding='utf-8')

            # Lưu ảnh vùng bảng
            tbl_rect = tbl.bbox
            tbl_pix = page.get_pixmap(matrix=mat, clip=fitz.Rect(tbl_rect))
            tbl_pix.save(str(OUT_DIR / f"{name}_table_{i}.png"))

            print(f"\n  Table {i}:")
            print(txt[:400])
            print(f"  → Saved: {txt_file.name}")

        summary.append((name, len(tables)))
        print()

    print("="*55)
    print("  TỔNG KẾT")
    print("="*55)
    for name, count in summary:
        status = "✅" if count > 0 else "❌ miss"
        print(f"  {status}  {name}: {count} table(s)")

if __name__ == '__main__':
    main()

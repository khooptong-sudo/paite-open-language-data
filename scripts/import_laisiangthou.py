"""Import the Laisiangthou Paite Bible into bible/laisiangthou/.

Source: assets/bible.db inside the Laisiangthou app APK by John Samte
(github.com/johnsamte), used with his permission.

English text comes from the World English Bible (public domain, ebible.org
eng-web_vpl), stored in bible/world-english-bible/, matched by book, chapter,
and verse.

Usage: python scripts/import_laisiangthou.py path/to/bible.db
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bible" / "laisiangthou"
WEB = ROOT / "bible" / "world-english-bible" / "eng-web_vpl.txt"

# Same codes as the legacy folders, in canonical order (book id 1..66).
BOOK_CODES = (
    "Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro "
    "Ecc Son Isa Jer Lam Eze Dan Hos Joe Amo Oba Jon Mic Nah Hab Zep Hag Zec Mal "
    "Mat Mar Luk Joh Act Rom 1Co 2Co Gal Eph Phi Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas "
    "1Pe 2Pe 1Jn 2Jn 3Jn Jde Rev"
).split()
HEADING_COLUMNS = ("title_0", "title", "title_1", "title_2", "title_3")
# Verse numbers that are wrong in the app database ("Book.chapter" -> {repeated number: correct number}).
# Gen 31 has two verse 23 rows; the second is 31:53 ("Abraham Pathian, Nahor Pathian").
VERSE_FIXES = {"Gen.31": {23: 53}}


def clean(text: str | None) -> str:
    """The app stores line breaks as a literal backslash-n and indents poetry."""
    return re.sub(r"\s+", " ", (text or "").replace("\\n", " ")).strip()


def load_web() -> dict[tuple[int, int, int], str]:
    """Lines look like 'GEN 1:1 In the beginning...'; books appear in canonical order."""
    english: dict[tuple[int, int, int], str] = {}
    book_ids: dict[str, int] = {}
    for line in WEB.read_text(encoding="utf-8").splitlines():
        book, ref, text = line.split(" ", 2)
        book_id = book_ids.setdefault(book, len(book_ids) + 1)
        chapter, verse = ref.split(":")
        english[(book_id, int(chapter), int(verse))] = text.strip()
    assert len(book_ids) == 66, f"expected 66 WEB books, got {len(book_ids)}"
    return english


def main(db_path: str) -> None:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT c.book_id, c.chapter_number, v.* FROM verses v "
        "JOIN Chapters c ON c.id = v.chapter_id WHERE c.book_id <= 66 "
        "ORDER BY c.book_id, c.chapter_number, v.verse_number"
    ).fetchall()

    chapters: dict[tuple[int, int], list[sqlite3.Row]] = {}
    for r in rows:
        chapters.setdefault((r["book_id"], r["chapter_number"]), []).append(r)

    web = load_web()
    verses = with_english = 0
    for (book_id, chapter), chapter_rows in chapters.items():
        code = BOOK_CODES[book_id - 1]
        out = []
        seen: set[int] = set()
        for r in chapter_rows:
            number = r["verse_number"]
            if number in seen:
                number = VERSE_FIXES[f"{code}.{chapter}"][number]
            seen.add(number)
            verse = {"verse": number, "paite": clean(r["text"])}
            heading = " / ".join(clean(r[c]) for c in HEADING_COLUMNS if clean(r[c]))
            if heading:
                verse["heading"] = heading
            english = web.get((book_id, chapter, number))
            if english:
                verse["english"] = english
                with_english += 1
            out.append(verse)
            verses += 1
        out.sort(key=lambda v: v["verse"])
        path = OUT / code / f"{chapter}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assert len(chapters) == 1189, f"expected 1189 chapters, got {len(chapters)}"
    print(f"{len(chapters)} chapters, {verses} verses, {with_english} with English")


if __name__ == "__main__":
    main(sys.argv[1])

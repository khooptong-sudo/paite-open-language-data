"""Import Google Form responses into corrections.json as pending entries.

In the form's response sheet: File > Download > Comma-separated values (.csv).
Then run:  python scripts/import_form_responses.py responses.csv

Columns are matched by keywords in their headings, so the question wording can
change. New entries get status "pending"; the maintainer sets "verified" after
checking them. Sentences that already exist in corrections.json are skipped.
"""

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORRECTIONS = ROOT / "corrections.json"

# field -> keywords that identify its column heading (first match wins, checked in this order).
# "min" is Paite for name: the live form asks "Peluttu Min".
COLUMNS = {
    "incorrect": ("wrong",),
    "paite": ("correct",),
    "english": ("english",),
    "register": ("spoken",),
    "notes": ("note",),
    "contributor": ("name", "min"),
}


def map_headers(headers: list[str]) -> dict[str, str]:
    found, used = {}, set()
    for field, keywords in COLUMNS.items():
        for h in headers:
            if h not in used and any(k in h.lower() for k in keywords):
                found[field] = h
                used.add(h)
                break
    missing = {"paite", "english"} - found.keys()
    if missing:
        sys.exit(f"Missing columns for: {', '.join(sorted(missing))}. Headings seen: {headers}")
    return found


def to_entry(row: dict[str, str], cols: dict[str, str], now: str) -> dict | None:
    get = lambda f: (row.get(cols[f]) or "").strip() if f in cols else ""
    paite, english = get("paite"), get("english")
    if not paite or not english:
        return None
    entry = {"paite": paite, "english": english}
    incorrect = get("incorrect")
    if incorrect and incorrect.lower() != paite.lower():
        entry["incorrect"] = incorrect
    register = get("register").lower()
    if register in ("spoken", "written"):
        entry["register"] = register
    notes = "; ".join(x for x in (get("notes"), f"from {get('contributor')}" if get("contributor") else "") if x)
    entry.update({"notes": notes or "Google Form submission", "status": "pending",
                  "added_at": now, "updated_at": now})
    return entry


def main(csv_path: str) -> None:
    data = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    known = {c["paite"].lower() for c in data["corrections"]}
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = map_headers(reader.fieldnames or [])
        added = skipped = 0
        for row in reader:
            entry = to_entry(row, cols, now)
            if entry is None or entry["paite"].lower() in known:
                skipped += 1
                continue
            data["corrections"].append(entry)
            known.add(entry["paite"].lower())
            added += 1

    data["meta"]["updated_at"] = now
    CORRECTIONS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added {added} pending corrections, skipped {skipped}.")


def _self_check() -> None:
    headers = ["Timestamp", "Wrong sentence (optional)", "Correct Paite sentence",
               "Meaning in English", "Spoken or written?", "Notes", "Your name (optional)"]
    cols = map_headers(headers)
    assert cols["paite"] == "Correct Paite sentence" and cols["incorrect"] == "Wrong sentence (optional)"
    row = dict(zip(headers, ["t", "Ka dam.", "Ka dam e.", "I am well.", "Spoken", "", "Mang"]))
    e = to_entry(row, cols, "now")
    assert e["incorrect"] == "Ka dam." and e["register"] == "spoken" and e["status"] == "pending"
    assert e["notes"] == "from Mang"
    assert to_entry(dict(row, **{"Correct Paite sentence": ""}), cols, "now") is None

    # Headings of the live form (forms.gle/dbAEPanWhszH8vK28).
    live = ["Timestamp", "Wrong Sentence (bawl dik di pen - optional)", "Correct Paite sentence/word",
            "Meaning in English", "Spoken or Written?", "Note:", "Peluttu Min"]
    assert map_headers(live) == {
        "incorrect": live[1], "paite": live[2], "english": live[3],
        "register": live[4], "notes": live[5], "contributor": live[6],
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-check"]:
        _self_check()
        print("self-check passed")
    else:
        main(sys.argv[1])

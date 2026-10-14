"""Build ready-to-train JSONL files in training/ from the source data.

Run after any change to the sources:  python scripts/build_training.py

Outputs (one JSON object per line, each with a fixed "split"):
  parallel.jsonl     Paite <-> English pairs, for translation
  monolingual.jsonl  Paite-only text, for language-model pretraining
  grammar.jsonl      incorrect -> correct Paite, for grammar correction
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "training"
BIBLE = ROOT / "bible" / "laisiangthou"


def split_for(group: str) -> str:
    """Stable 90/5/5 split. Group whole chapters so test verses never leak into train."""
    bucket = int(hashlib.sha256(group.encode("utf-8")).hexdigest(), 16) % 100
    return "train" if bucket < 90 else "dev" if bucket < 95 else "test"


# Sentences in the benchmark (eval/everyday.jsonl) must never be trained on.
EVAL_PAITE = {
    p.lower()
    for line in (ROOT / "eval" / "everyday.jsonl").read_text(encoding="utf-8").splitlines() if line
    for p in json.loads(line)["paite"]
}


def split_for_sentence(paite: str, row_id: str) -> str:
    return "test" if paite.lower() in EVAL_PAITE else split_for(row_id)


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write(name: str, rows: list[dict]) -> None:
    with open(OUT / name, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    parallel, mono, grammar = [], [], []

    for path in sorted(BIBLE.glob("*/*.json")):
        ref = f"{path.parent.name}.{path.stem}"
        for v in json.loads(path.read_text(encoding="utf-8")):
            row_id = f"bible:{ref}.{v['verse']}"
            mono.append({"id": row_id, "text": v["paite"], "source": "bible", "split": split_for(ref)})
            if v.get("english"):
                parallel.append({"id": row_id, "paite": v["paite"], "english": v["english"],
                                 "source": "bible", "split": split_for(ref)})

    for i, c in enumerate(load("corrections.json")["corrections"]):
        if c.get("status") != "verified":
            continue
        row_id = f"correction:{i}"
        parallel.append({"id": row_id, "paite": c["paite"], "english": c["english"],
                         "source": "correction", "split": split_for_sentence(c["paite"], row_id)})
        if c.get("incorrect"):
            grammar.append({"id": row_id, "incorrect": c["incorrect"], "correct": c["paite"],
                            "register": c.get("register", "unspecified"), "notes": c.get("notes", ""),
                            "split": split_for_sentence(c["paite"], row_id)})

    book = load("paite_phrasebook.json")
    for english, paite in book["verified_examples"].items():
        row_id = f"example:{english}"
        parallel.append({"id": row_id, "paite": paite, "english": english,
                         "source": "verified_example", "split": split_for_sentence(paite, row_id)})
    for english, paite in book["verified_words"].items():
        parallel.append({"id": f"word:{english}", "paite": paite, "english": english,
                         "source": "verified_word", "split": "train"})
    for path in sorted((ROOT / "community").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            variants = [row["paite"], *row.get("also_correct", [])]
            split = "test" if any(p.lower() in EVAL_PAITE for p in variants) else split_for(row["id"])
            for k, paite in enumerate(variants):
                row_id = row["id"] if k == 0 else f"{row['id']}:{k}"
                parallel.append({"id": row_id, "paite": paite, "english": row["english"],
                                 "source": "community", "split": split})

    songs = load("songs/Kristian+Labu_1_4_53_apkcombo_com.json")["songs"]
    for i, s in enumerate(songs):
        row_id = f"hymn:{i}"
        mono.append({"id": row_id, "text": s["lyrics"], "source": "hymn", "split": split_for(row_id)})

    dictionary = load("dictionary/Paite+English+Dictionary_1_1_4_apkcombo_com.json")["dictionary"]
    for i, d in enumerate(dictionary):
        if d.get("english") and d.get("paite"):
            # Word lists help vocabulary, not held-out evaluation, so always train.
            parallel.append({"id": f"dict:{i}", "paite": d["paite"], "english": d["english"],
                             "source": "dictionary", "split": "train"})

    write("parallel.jsonl", parallel)
    write("monolingual.jsonl", mono)
    write("grammar.jsonl", grammar)

    ids = [r["id"] for r in parallel]
    assert len(ids) == len(set(ids)), "duplicate ids in parallel.jsonl"


if __name__ == "__main__":
    main()

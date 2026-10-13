"""How well does an AI model know Paite? Score it on eval/everyday.jsonl.

Each sentence is translated both ways (Paite -> English, English -> Paite) and
scored with chrF (0-100, higher is better) against every accepted answer; the
best match counts. Works with any OpenAI-compatible chat API.

Examples:
  # OpenRouter: one key for Claude, GPT, Gemini, Llama ...
  set EVAL_API_KEY=...   (PowerShell: $env:EVAL_API_KEY = '...')
  # Model ids are listed at https://openrouter.ai/models (copy them exactly)
  python scripts/run_eval.py <model-id> <model-id> ...

  # Local Ollama, no key
  python scripts/run_eval.py --base-url http://localhost:11434/v1 llama3.1

Writes eval/results/<model>.jsonl (every answer) and rebuilds eval/RESULTS.md.
After accepted answers in eval/everyday.jsonl change:  python scripts/run_eval.py --rescore
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
PAITE = "Paite (a Zomi language of Manipur, Mizoram and Myanmar; ISO 639-3: pck)"


def chrf(hypothesis: str, reference: str, max_n: int = 6, beta: float = 2.0) -> float:
    """chrF as in Popovic (2015): character n-grams without spaces, recall weighted 2x."""
    hyp, ref = re.sub(r"\s+", "", hypothesis), re.sub(r"\s+", "", reference)
    precisions, recalls = [], []
    for n in range(1, max_n + 1):
        h = Counter(hyp[i:i + n] for i in range(len(hyp) - n + 1))
        r = Counter(ref[i:i + n] for i in range(len(ref) - n + 1))
        if not h or not r:
            continue
        match = sum((h & r).values())
        precisions.append(match / sum(h.values()))
        recalls.append(match / sum(r.values()))
    if not precisions:
        return 0.0
    p, r = sum(precisions) / len(precisions), sum(recalls) / len(recalls)
    return 0.0 if p + r == 0 else 100 * (1 + beta**2) * p * r / (beta**2 * p + r)


def ask(base_url: str, model: str, prompt: str) -> str:
    body = json.dumps({"model": model, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if os.environ.get("EVAL_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["EVAL_API_KEY"]
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", body, headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["choices"][0]["message"]["content"].strip()


def prompt_for(text: str, source: str, target: str) -> str:
    return (f"Translate this {source} sentence into {target}. "
            f"Reply with the translation only, nothing else.\n\n{text}")


def load_items() -> list[dict]:
    return [json.loads(line) for line in (EVAL / "everyday.jsonl").read_text(encoding="utf-8").splitlines() if line]


def references(item: dict, direction: str) -> list[str]:
    return item["english"] if direction == "pck-en" else item["paite"]


def results_path(model: str) -> Path:
    return EVAL / "results" / (re.sub(r"[^\w.-]+", "_", model) + ".jsonl")


def save(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def evaluate(base_url: str, model: str) -> list[dict]:
    rows, date = [], time.strftime("%Y-%m-%d")
    for item in load_items():
        for direction, src_lang, tgt_lang, src in (
            ("pck-en", PAITE, "English", item["paite"][0]),
            ("en-pck", "English", PAITE, item["english"][0]),
        ):
            try:
                prediction = ask(base_url, model, prompt_for(src, src_lang, tgt_lang))
            except Exception as e:  # keep going; a failed call scores 0 and is recorded
                prediction = f"[error: {e}]"
            refs = references(item, direction)
            rows.append({"model": model, "date": date, "id": item["id"], "direction": direction,
                         "source": src, "prediction": prediction, "references": refs,
                         "chrf": round(max(chrf(prediction, r) for r in refs), 1)})
    save(results_path(model), rows)
    return rows


def rescore() -> None:
    """Re-score saved answers against the current accepted answers, without calling any model."""
    items = {i["id"]: i for i in load_items()}
    for path in sorted((EVAL / "results").glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        for r in rows:
            if r["id"] in items:
                r["references"] = references(items[r["id"]], r["direction"])
                r["chrf"] = round(max(chrf(r["prediction"], ref) for ref in r["references"]), 1)
        save(path, rows)


def summarize(rows: list[dict]) -> dict:
    by_dir = {d: [r["chrf"] for r in rows if r["direction"] == d] for d in ("pck-en", "en-pck")}
    return {d: sum(s) / len(s) if s else 0.0 for d, s in by_dir.items()} | {"n": len({r["id"] for r in rows})}


def write_results() -> None:
    """Rebuild eval/RESULTS.md from every file in eval/results/."""
    lines = ["# How well does AI know Paite?", "",
             "chrF scores (0-100, higher is better) on `eval/everyday.jsonl`, sentences checked by a native speaker.",
             "chrF compares letters, not meaning, so a correct answer in other words scores below 100. "
             "Every answer is in `eval/results/`.", "",
             "| Date | Model | Paite → English | English → Paite | Sentences |",
             "|------|-------|-----------------|-----------------|-----------|"]
    for path in sorted((EVAL / "results").glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        s = summarize(rows)
        lines.append(f"| {rows[0].get('date', '')} | `{rows[0].get('model', path.stem)}` | "
                     f"{s['pck-en']:.1f} | {s['en-pck']:.1f} | {s['n']} |")
    (EVAL / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _self_check() -> None:
    assert chrf("Ka dam e.", "Ka dam e.") == 100
    assert chrf("", "Ka dam e.") == 0
    assert 0 < chrf("Ka dam.", "Ka dam e.") < 100
    assert chrf("Ka dam e.", "Ka dam e.") > chrf("Ka dam hi.", "Ka dam e.") > chrf("I am well.", "Ka dam e.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("models", nargs="*")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--rescore", action="store_true", help="re-score saved answers after accepted answers change")
    args = parser.parse_args()
    if args.self_check:
        _self_check()
        print("self-check passed")
    if args.rescore:
        rescore()
    for model in args.models:
        s = summarize(evaluate(args.base_url, model))
        print(f"{model}: Paite→English {s['pck-en']:.1f}, English→Paite {s['en-pck']:.1f}")
    if args.rescore or args.models:
        write_results()
        print((EVAL / "RESULTS.md").read_text(encoding="utf-8"))

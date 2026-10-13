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

Writes eval/results/<model>.jsonl (every answer) and adds a row to eval/RESULTS.md.
"""

import argparse
import json
import os
import re
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


def evaluate(base_url: str, model: str) -> dict[str, float]:
    items = [json.loads(line) for line in (EVAL / "everyday.jsonl").read_text(encoding="utf-8").splitlines() if line]
    rows, totals = [], {"pck-en": [], "en-pck": []}
    for item in items:
        for direction, src_lang, tgt_lang, src, refs in (
            ("pck-en", PAITE, "English", item["paite"][0], item["english"]),
            ("en-pck", "English", PAITE, item["english"][0], item["paite"]),
        ):
            try:
                prediction = ask(base_url, model, prompt_for(src, src_lang, tgt_lang))
            except Exception as e:  # keep going; a failed call scores 0 and is recorded
                prediction = f"[error: {e}]"
            score = max(chrf(prediction, ref) for ref in refs)
            totals[direction].append(score)
            rows.append({"id": item["id"], "direction": direction, "source": src,
                         "prediction": prediction, "references": refs, "chrf": round(score, 1)})

    out = EVAL / "results" / (re.sub(r"[^\w.-]+", "_", model) + ".jsonl")
    out.parent.mkdir(exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return {d: sum(s) / len(s) for d, s in totals.items()} | {"n": len(items)}


def record(model: str, scores: dict[str, float]) -> None:
    results = EVAL / "RESULTS.md"
    if not results.exists():
        results.write_text(
            "# How well does AI know Paite?\n\n"
            "chrF scores (0-100, higher is better) on `eval/everyday.jsonl`, sentences checked by a native speaker.\n\n"
            "| Date | Model | Paite → English | English → Paite | Sentences |\n"
            "|------|-------|-----------------|-----------------|-----------|\n", encoding="utf-8")
    with open(results, "a", encoding="utf-8") as f:
        f.write(f"| {time.strftime('%Y-%m-%d')} | `{model}` | {scores['pck-en']:.1f} | "
                f"{scores['en-pck']:.1f} | {scores['n']} |\n")


def _self_check() -> None:
    assert chrf("Ka dam e.", "Ka dam e.") == 100
    assert chrf("", "Ka dam e.") == 0
    assert 0 < chrf("Ka dam.", "Ka dam e.") < 100
    assert chrf("Ka dam e.", "Ka dam e.") > chrf("Ka dam hi.", "Ka dam e.") > chrf("I am well.", "Ka dam e.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("models", nargs="*")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _self_check()
        print("self-check passed")
    for model in args.models:
        scores = evaluate(args.base_url, model)
        record(model, scores)
        print(f"{model}: Paite→English {scores['pck-en']:.1f}, English→Paite {scores['en-pck']:.1f}")

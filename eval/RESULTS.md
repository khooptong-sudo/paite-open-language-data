# How well does AI know Paite?

chrF scores (0-100, higher is better) on `eval/everyday.jsonl`, sentences checked by a native speaker.
chrF compares letters, not meaning, so a correct answer in other words scores below 100. Every answer is in `eval/results/`.

| Date | Model | Paite → English | English → Paite | Sentences |
|------|-------|-----------------|-----------------|-----------|
| 2026-10-13 | `deepseek-chat` | 43.2 | 45.4 | 16 |
| 2026-10-13 | `deepseek-reasoner` | 57.4 | 43.1 | 16 |

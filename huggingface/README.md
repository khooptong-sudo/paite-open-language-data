---
language:
  - pck
  - en
license: other
license_name: mixed
license_link: https://github.com/khooptong-sudo/paite-open-language-data/blob/master/LICENSE
pretty_name: Paite Open Language Data
task_categories:
  - translation
  - text-generation
tags:
  - paite
  - zomi
  - low-resource
  - parallel-corpus
  - grammatical-error-correction
size_categories:
  - 10K<n<100K
configs:
  - config_name: parallel
    data_files: training/parallel.jsonl
  - config_name: monolingual
    data_files: training/monolingual.jsonl
  - config_name: everyday_eval
    data_files: eval/everyday.jsonl
  - config_name: community
    data_files: community/*.jsonl
---

# Paite Open Language Data

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23349155.svg)](https://doi.org/10.5281/zenodo.23349155)

Open training data for Paite (ISO 639-3 `pck`, Glottolog `pait1244`), an independent Tibeto-Burman language spoken mainly in Churachandpur district, Manipur, India, with communities in Mizoram, Assam and Myanmar. The 2011 Census of India counted 78,725 people whose mother tongue is Paite. The target is modern Paite as it is spoken and written today.

**At a glance (16 Nov 2026):** 1,405 everyday sentence pairs written and checked by speakers on [Paite Daily](https://paite.lamkalabs.com) · 62 voice recordings · 1,902 word-list entries · the complete Paite Bible aligned with English · 32,943 parallel training rows.

Source data, audio, scripts, and documentation: https://github.com/khooptong-sudo/paite-open-language-data

## Configurations

| Config | Rows | One row |
|--------|------|---------|
| `parallel` | 32,943 | `id`, `paite`, `english`, `source`, `split` |
| `monolingual` | 31,104 | `id`, `text`, `source`, `split` |
| `grammar` | added here once it has rows; see `training/grammar.jsonl` on GitHub | `id`, `incorrect`, `correct`, `register`, `notes`, `split` |
| `community` | 1,405, grows weekly | `id`, `direction`, `english`, `paite`, `register`, `contributor`, `verified_by`, `verified_at`, `also_correct`, `explanation`: every pair verified on [Paite Daily](https://paite.lamkalabs.com), a reviewer's correction standing over the submission |
| `everyday_eval` | 16 | `id`, `paite` (accepted answers), `english` (accepted answers) |

Each training row has a fixed `split` (`train`, `dev`, `test`; about 90/5/5). Whole Bible chapters stay in one split. Every `everyday_eval` sentence is in the `test` split, so a model is never trained on the benchmark.

```python
from datasets import load_dataset

pairs = load_dataset("LamkaLabs/paite-open-language-data", "parallel")["train"]
train = pairs.filter(lambda r: r["split"] == "train")
```

## Sources and rights

| Part | Source | Rights |
|------|--------|--------|
| Paite Bible | Laisiangthou app by [John Samte](https://github.com/johnsamte) | Used with permission; credit John Samte |
| English Bible | World English Bible | Public domain |
| Corrections, benchmark | Native-speaker contributors | CC BY 4.0 |
| Paite Daily translations (`community/`) | Paite Daily contributors, verified by reviewers | Per line, in the `licence` field: CC0 1.0 (answers before 21 Oct 2026) or CC BY 4.0 (after) |
| Voice recordings (`audio/`) | Paite Daily speakers, accepted by a reviewer | CC BY 4.0 |
| Scripts | Maintainer | MIT or Apache 2.0 |

The 62 voice recordings are in `audio/` here and on GitHub; `audio/recordings.jsonl` links each clip to its `community/` line, speaker and length.

Full terms: [LICENSE](https://github.com/khooptong-sudo/paite-open-language-data/blob/master/LICENSE).

## Benchmark

How well do AI models know everyday Paite? See [eval/RESULTS.md](https://github.com/khooptong-sudo/paite-open-language-data/blob/master/eval/RESULTS.md).

## Contribute

Native speakers: send a correction with the [Paite Correction form](https://forms.gle/dbAEPanWhszH8vK28). No account is needed.

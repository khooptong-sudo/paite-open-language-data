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
---

# Paite Open Language Data

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23349155.svg)](https://doi.org/10.5281/zenodo.23349155)

Training data for Paite (ISO 639-3: `pck`), a Zomi language of Manipur and Mizoram (India), Myanmar, and Bangladesh. This is the target language: modern Paite, not the Tedim (Tedim-Chin) style of older Bible text.

Source data, scripts, and documentation: https://github.com/khooptong-sudo/paite-open-language-data

## Configurations

| Config | Rows | One row |
|--------|------|---------|
| `parallel` | 54,146 | `id`, `paite`, `english`, `source`, `split` |
| `monolingual` | 31,677 | `id`, `text`, `source`, `split` |
| `grammar` | added here once it has rows; see `training/grammar.jsonl` on GitHub | `id`, `incorrect`, `correct`, `register`, `notes`, `split` |
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
| Corrections, verified sentences, benchmark | Native-speaker contributors | CC BY 4.0 |
| Dictionary, hymns | Third-party Android apps | Not licensed by this dataset; research use |

Full terms: [LICENSE](https://github.com/khooptong-sudo/paite-open-language-data/blob/master/LICENSE).

## Benchmark

How well do AI models know everyday Paite? See [eval/RESULTS.md](https://github.com/khooptong-sudo/paite-open-language-data/blob/master/eval/RESULTS.md).

## Contribute

Native speakers: send a correction with the [Paite Correction form](https://forms.gle/dbAEPanWhszH8vK28). No account is needed.

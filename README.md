# Paite Open Language Data

Open text data for the Paite language, ready for research, language learning, and training language models.

Paite (ISO 639-3: `pck`) is a Zomi language of the Tibeto-Burman branch of the Sino-Tibetan family. The Paite are a distinct tribe within the Zomi people, who live in Manipur and Mizoram (India), Myanmar, and the Chittagong Hill Tracts (Bangladesh). Paite is mutually intelligible with Tedim (Zopau) and the other Zomi languages. Some linguistic catalogues file this language group under a technical subgroup label. That label is linguistic, not ethnic.

References: [Paite people](https://en.wikipedia.org/wiki/Paite_people), [Tedim language](https://en.wikipedia.org/wiki/Tedim_language), [Zomi identity among the Paite of Manipur (NEHU thesis)](https://dspace.nehu.ac.in/bitstreams/c81ef78a-e800-434a-8661-53b6b96006b5/download).

Paite has very little digital text. This repository puts the text that we have in one place, in plain JSON, so that any person can use it without a scraper.

## Contents

| Path | Contents | Size |
|------|----------|------|
| `training/` | **Ready-to-train JSONL files** with fixed train, dev, and test splits. Start here. | See [Training a model](#training-a-model) |
| `bible/laisiangthou/` | **Primary Bible.** The complete Laisiangthou Paite Bible by [John Samte](https://github.com/johnsamte), one JSON file for each chapter | 66 books, 1,189 chapters, 31,104 verses |
| `bible/world-english-bible/` | World English Bible (public domain) in verse-per-line form, the English side of every Bible pair | 66 books, 31,103 verses |
| `bible/legacy-etabetapi/` | Retired Bible text, kept for reference and comparison. Do not use it as a primary source. | 22 books, 408 chapters |
| `dictionary/` | English to Paite dictionary with part of speech | 23,006 entries |
| `songs/` | Paite hymn lyrics, with English titles and authors, and hymn-app snippets | 573 hymns, 846 snippets |
| `corrections.json` | Sentences that a native speaker checked and corrected | Grows over time |
| `grammar_notes.md` | Working notes on pronouns, verbs, and particles | Hypotheses, not a formal grammar |
| `paite_phrasebook.json` | Combined lookup file that the Levia assistant uses | 21,324 dictionary entries, 573 hymns |
| `scripts/` | The scripts that build `bible/laisiangthou/` and `training/` | |

## Training a model

The repository holds training **data**, not a trained model. You train a model on it with your own tools. The Levia assistant is one example. A Hugging Face fine-tuning script is another.

| File | One line contains | Use it to train |
|------|-------------------|-----------------|
| `training/parallel.jsonl` | `{"id", "paite", "english", "source", "split"}` | Translation between Paite and English |
| `training/monolingual.jsonl` | `{"id", "text", "source", "split"}` | A language model that writes natural Paite |
| `training/grammar.jsonl` | `{"id", "incorrect", "correct", "register", "notes", "split"}` | Grammar correction for spoken and written Paite |

- **Splits are fixed.** About 90% of rows are `train`, 5% are `dev`, and 5% are `test`. A whole Bible chapter always stays in one split, so test verses never leak into training. Dictionary entries and single words are always `train`.
- **`source`** tells you where a row came from (`bible`, `hymn`, `dictionary`, `correction`, `verified_example`, `verified_word`). Filter on it to weight or remove a source.
- **Grammar data starts empty.** `grammar.jsonl` grows when speakers add corrections that include the wrong form (see [CONTRIBUTING.md](CONTRIBUTING.md)). This is the most valuable data that you can give.

Load the files with the Hugging Face `datasets` library:

```python
from datasets import load_dataset

ds = load_dataset("json", data_files="training/parallel.jsonl")["train"]
train = ds.filter(lambda r: r["split"] == "train")
test = ds.filter(lambda r: r["split"] == "test")
```

After you change any source file, rebuild the training files:

```bash
python scripts/build_training.py
```

## File formats

**`bible/laisiangthou/<Book>/<chapter>.json`**: a list of verses. `english` (World English Bible) is present for 31,095 of the 31,104 verses. `heading` is the section heading in the Paite Bible.

```json
[{ "verse": 1, "paite": "Atung in Pathian in lei leh vante asiam hi.", "heading": "Thilsiam Thu", "english": "In the beginning God ... created the heavens and the earth." }]
```

Book folders use three-character codes: `Gen`, `Exo`, `Lev` ... `Mat`, `Mar`, `Luk`, `Joh` ... `Jde`, `Rev`.

**`corrections.json`**: `{ "meta": {...}, "corrections": [ { "paite", "english", "incorrect"?, "register"?, "notes", "status", "added_at", "updated_at" } ] }`. Only entries with `"status": "verified"` go into the training files.

**`paite_phrasebook.json`**: one object with the keys `dictionary`, `verified_words`, `verified_examples`, `verified_corrections`, `corpus_examples`, and `song_titles`. The keys `greetings`, `courtesy`, and `common` hold placeholders that are not filled in yet.

## Possible uses

- Grammar and spelling correction for spoken and written Paite.
- Machine translation between Paite and English.
- Dictionary lookup and keyboard word lists.
- Language learning material and flash cards.
- Linguistic research on Zomi morphology and particles.
- Evaluation sets for large language models on a low-resource language.

## Known limitations

- **Register.** Most sentences come from the Bible and hymns. Formal and religious language is over-represented. Everyday speech is rare. Corrections from conversation are the best way to fix this.
- **Nine verses have no English.** The World English Bible omits or moves 9 verses that the Paite Bible keeps (for example, Acts 8:37, Luke 17:36, and Romans 16:25-27). These rows are in `monolingual.jsonl` only.
- **Dictionary quality.** The dictionary comes from an app. Some entries contain typing errors or several meanings in one string.
- **One fixed source error.** In the app database, Genesis 31:53 has the number 23. The import script corrects it.

## Sources and rights

This repository mixes original work and third-party text. The licence is different for each part. Read [LICENSE](LICENSE) before you redistribute the data.

| Part | Source | Rights |
|------|--------|--------|
| `corrections.json`, `grammar_notes.md`, `verified_*` entries, scripts, documentation | Maintainer and native-speaker contributors | CC BY 4.0 |
| Paite Bible in `bible/laisiangthou/` | Laisiangthou app (v5.0.2) by [John Samte](https://github.com/johnsamte) | Used with the permission of John Samte |
| English Bible text | World English Bible ([ebible.org](https://ebible.org/find/details.php?id=eng-web)) | Public domain |
| Paite Bible in `bible/legacy-etabetapi/` (retired) | Collected from etabetapi.com | Copyright of the original Paite Bible publisher |
| Dictionary | Extracted from the "Paite English Dictionary" Android app (v1.1.4) | Copyright of the app author |
| Hymn lyrics | Extracted from the "Kristian Labu" (v1.4.53) and "Biakna Labupi" (v1.0.0) Android apps | Copyright of the hymn authors, translators, and app publishers |
| UDHR example sentences | Universal Declaration of Human Rights, Paite translation | Public use permitted by the United Nations |

The third-party text is included for non-commercial research and language preservation. We do not claim ownership of it. If you own any of this text and want it removed or credited differently, open an issue. We will respond quickly.

## Credits

- **John Samte** ([github.com/johnsamte](https://github.com/johnsamte)) gave permission to use his Laisiangthou Bible, the primary Bible text in this repository.
- Native speakers who send corrections are credited in the git history.

## Contributing

Native speakers can help the most. See [CONTRIBUTING.md](CONTRIBUTING.md) to send a correction, a new phrase, or a grammar note.

## Citation

If you use this data in a paper, cite it with the details in [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button for it.

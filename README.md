# Paite Open Language Data

Open text data for the Paite language, for research, language learning, and language technology.

Paite (ISO 639-3: `pck`) is a Zomi language of the Tibeto-Burman branch of the Sino-Tibetan family. The Paite are a distinct tribe within the Zomi people, who live in Manipur and Mizoram (India), Myanmar, and the Chittagong Hill Tracts (Bangladesh). Paite is mutually intelligible with Tedim (Zopau) and the other Zomi languages. Some linguistic catalogues file this language group under a technical subgroup label. That label is linguistic, not ethnic. Paite has very little digital text.

References: [Paite people](https://en.wikipedia.org/wiki/Paite_people), [Tedim language](https://en.wikipedia.org/wiki/Tedim_language), [Zomi identity among the Paite of Manipur (NEHU thesis)](https://dspace.nehu.ac.in/bitstreams/c81ef78a-e800-434a-8661-53b6b96006b5/download). This repository puts the text that we have in one place, in plain JSON and text files, so that any person can use it without a scraper.

## Contents

| Path | Contents | Size |
|------|----------|------|
| `paite_phrasebook.json` | Combined lookup file: dictionary, verified words and phrases, owner corrections, Bible examples, and hymn lyrics | 21,324 dictionary entries, 2,000 Bible examples, 573 hymns |
| `parallel.txt` | Paite and English Bible verse pairs, one pair for each block | 10,471 verse pairs |
| `<Book>/<chapter>.json` | The same Bible verses, one file for each chapter (for example `Gen/1.json`) | 22 books, 408 chapters |
| `songs/Kristian+Labu_*.json` | Paite hymn lyrics with English titles and authors | 573 hymns |
| `songs/Biakna+Labupi_*.json` | Text snippets from a Paite hymn app | 846 snippets |
| `songs/Paite+English+Dictionary_*.json` | English to Paite dictionary with part of speech | 23,006 entries |
| `corrections.json` | Audit trail of sentences that a native speaker checked and corrected | Grows over time |
| `grammar_notes.md` | Working notes on pronouns, verbs, and particles | Hypotheses, not a formal grammar |

### Bible coverage

The Bible text covers 22 books: Genesis, Leviticus, Numbers, Nehemiah, Job, Isaiah, Jeremiah, Lamentations, Daniel, Hosea, Micah, Nahum, Habakkuk, Haggai, Malachi, Romans, Galatians, Ephesians, Colossians, Hebrews, James, and Revelation. The other books are not in this release.

## File formats

**`parallel.txt`**: UTF-8 text. Each verse pair is two lines, then one blank line.

```text
PAITE: A tungin Pathianin lei leh van a siam.
ENGLISH: In the beginning God ... created the heavens and the earth.
```

**`<Book>/<chapter>.json`**: a list of verses.

```json
[{ "verse": 1, "paite": "A tungin Pathianin lei leh van a siam.", "english": "In the beginning God ..." }]
```

**`paite_phrasebook.json`**: one object. Each key holds a map of entries.

| Key | Map from | Map to |
|-----|----------|--------|
| `dictionary` | English word or Paite word | Translation or definition |
| `verified_words` | English word | Paite word, checked by a native speaker |
| `verified_examples` | English sentence | Paite sentence, checked |
| `verified_corrections` | Paite sentence | English meaning, checked |
| `corpus_examples` | English Bible verse | Paite Bible verse |
| `song_titles` | Hymn title | Paite lyrics |
| `greetings`, `courtesy`, `common` | English phrase | Placeholder text. These entries are not filled in yet. |

**`corrections.json`**: `{ "meta": {...}, "corrections": [ { "paite", "english", "notes", "status", "added_at", "updated_at" } ] }`. Only entries with `"status": "verified"` are checked.

## Quick start

```python
import json

with open("paite_phrasebook.json", encoding="utf-8") as f:
    book = json.load(f)

print(book["dictionary"]["language"])        # Pau, Ham, Kampau
print(book["verified_corrections"]["Ka dam e."])  # I am well.

pairs = []
with open("parallel.txt", encoding="utf-8") as f:
    for block in f.read().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) == 2:
            pairs.append((lines[0].removeprefix("PAITE: "), lines[1].removeprefix("ENGLISH: ")))
print(len(pairs))  # 10471
```

## Possible uses

- Machine translation between Paite and English (the Bible pairs are sentence-aligned).
- Dictionary lookup, spell checking, and keyboard word lists.
- Language learning material and flash cards.
- Linguistic research on Zomi morphology and particles.
- Evaluation sets for large language models on a low-resource language.

## Known limitations

- **Register.** Most sentences come from the Bible and hymns. Formal and religious language is over-represented. Everyday speech is rare.
- **Footnotes in English verses.** Some English verses contain translator footnotes inside the sentence (for example, a note on the Hebrew word "Elohim"). Remove them before you train a model.
- **Dictionary quality.** The dictionary comes from an app. Some entries contain typing errors or several meanings in one string.
- **Two empty verses.** Two Bible verses have no English text.
- **Grammar notes are hypotheses.** Each note marked with `?` is not confirmed.

## Sources and rights

This repository mixes original work and third-party text. The licence is different for each part. Read [LICENSE](LICENSE) before you redistribute the data.

| Part | Source | Rights |
|------|--------|--------|
| `corrections.json`, `grammar_notes.md`, `verified_*` entries, documentation | Maintainer and native-speaker contributors | CC BY 4.0 |
| English Bible text | World English Bible | Public domain |
| Paite Bible text | Collected from etabetapi.com | Copyright of the original Paite Bible publisher |
| Dictionary | Extracted from the "Paite English Dictionary" Android app (v1.1.4) | Copyright of the app author |
| Hymn lyrics | Extracted from the "Kristian Labu" (v1.4.53) and "Biakna Labupi" (v1.0.0) Android apps | Copyright of the hymn authors, translators, and app publishers |
| UDHR example sentences | Universal Declaration of Human Rights, Paite translation | Public use permitted by the United Nations |

The third-party text is included for non-commercial research and language preservation. We do not claim ownership of it. If you own any of this text and want it removed or credited differently, open an issue. We will respond quickly.

## Contributing

Native speakers can help the most. See [CONTRIBUTING.md](CONTRIBUTING.md) to send a correction, a new phrase, or a grammar note.

## Citation

If you use this data in a paper, cite it with the details in [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button for it.

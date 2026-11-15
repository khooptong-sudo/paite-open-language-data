# Paite Open Language Data

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23349155.svg)](https://doi.org/10.5281/zenodo.23349155)

Open text and speech data for the Paite language, ready for research, language learning, and building language tools.

**At a glance (16 Nov 2026):** 1,405 Paite–English sentence pairs written and checked by speakers on [Paite Daily](https://paite.lamkalabs.com) · 62 voice recordings · 1,902 word-list entries · the complete Paite Bible aligned verse by verse with English · 55,814 ready-to-train parallel rows. The community parts grow every night.

## About Paite

Paite (ISO 639-3 `pck`, Glottolog `pait1244`) is an independent Tibeto-Burman language. Most speakers live in Churachandpur district, Manipur, India, where Lamka is the main town. There are also Paite communities in Mizoram and Assam, and Paite families in Myanmar. The Paites are one of the Zo (Zomi) peoples. This repository targets modern Paite as it is spoken and written today.

- **78,725** people gave Paite as their mother tongue in the 2011 Census of India.
- **1903:** T. Vialphung made the Paite alphabet (*Paite Laimal*).
- **1993, 2003, 2014:** editions of the Paite Tribe Council's *English–Paite Dictionary*.
- **2004:** Manipur University made Paite a subject in its three-year degree course.
- **2006:** Naorem Saratchandra Singh's *A Grammar of Paite* (Mittal), the only book-length reference grammar.
- All India Radio Imphal broadcasts in Paite every day.
- The Endangered Languages Project and Glottolog list Paite as *vulnerable*, with low certainty.

Paite is well written down, but it has very little digital text, and no spellchecker, predictive keyboard or translation tool. This repository puts the text and speech that exist in one place, in plain JSON, so that anyone can use it without a scraper.

References: [Paite people (Wikipedia)](https://en.wikipedia.org/wiki/Paite_people), [Glottolog: Paite](https://glottolog.org/resource/languoid/iso/pck), [Paite Daily: About](https://paite.lamkalabs.com/about).

## New here? Start with these questions

<details>
<summary><b>What is this, in simple words?</b></summary>

It is a free collection of Paite writing, kept in one place online. Computers learn a language by reading a very large amount of it. Paite has almost no text online, so apps like Google Translate and ChatGPT get it wrong. This collection gives computers Paite to learn from.

</details>

<details>
<summary><b>Is this an app?</b></summary>

No. It is the material that apps are built from. A developer can use it to make a Paite keyboard, a translator, a spell checker, or a grammar checker.

</details>

<details>
<summary><b>What is inside?</b></summary>

Everyday sentences in Paite and English that speakers wrote and other speakers checked, with recordings of people reading them aloud. Also the complete Paite Bible, matched verse by verse with English, a dictionary of about 23,000 words, and 573 hymns.

</details>

<details>
<summary><b>Why the Bible?</b></summary>

It is the largest text that exists in both Paite and English, one verse at a time. Matched sentences in two languages are the best material to teach a computer to translate. The Paite text is the Laisiangthou translation by John Samte, used with his permission.

</details>

<details>
<summary><b>Who owns it? Does it cost money?</b></summary>

It is free. Students, researchers, developers, and anyone curious can download it. Some parts come from other people, and [LICENSE](LICENSE) gives the details.

</details>

<details>
<summary><b>Can I help? I do not know about computers.</b></summary>

Yes. If you speak Paite well, you can help more than any programmer. When you see a Paite sentence that is wrong, send the correct one. **Play [Paite Daily](https://paite.lamkalabs.com/)**: translate one simple sentence a day, on your phone, with no account. To fix a wrong sentence you have seen, use the **[Paite Correction form](https://forms.gle/dbAEPanWhszH8vK28)** with the wrong sentence, the correct sentence, and its meaning in English. It takes one minute on a phone, and you do not need an account. If you use GitHub, you can also use the [GitHub correction form](https://github.com/khooptong-sudo/paite-open-language-data/issues/new?template=correction.yml).

</details>

<details>
<summary><b>Why does this matter?</b></summary>

Everything is moving to phones and AI. A language with no digital text gets left behind, and the next generation types in another language. This work helps Paite keep up.

</details>

## Contents

| Path | Contents | Size |
|------|----------|------|
| `community/` | **Everyday sentence pairs from Paite Daily**, each written by one speaker and checked by another. Each line's `licence` field says CC0 1.0 or CC BY 4.0 | 1,405 pairs, grows nightly |
| `audio/` | **Speakers reading checked Paite lines aloud**, from Paite Daily, each clip accepted by a reviewer (CC BY 4.0). `audio/recordings.jsonl` lists each clip with its line (`text_id` matches the `id` in `community/`), speaker and length | 62 clips, grows nightly |
| `glossary.json` | Paite words and meanings from Paite Daily contributors, checked by reviewers | 1,902 entries, grows nightly |
| `training/` | **Ready-to-train JSONL files** with fixed train, dev, and test splits | See [Training a model](#training-a-model) |
| `bible/laisiangthou/` | **Primary Bible.** The complete Laisiangthou Paite Bible by [John Samte](https://github.com/johnsamte), one JSON file for each chapter | 66 books, 1,189 chapters, 31,104 verses |
| `bible/world-english-bible/` | World English Bible (public domain) in verse-per-line form, the English side of every Bible pair | 66 books, 31,103 verses |
| `bible/legacy-etabetapi/` | Retired Bible text in an older Bible style, kept for reference and comparison. It is not modern Paite. Do not use it as a primary source. | 22 books, 408 chapters |
| `dictionary/` | English to Paite dictionary with part of speech | 23,006 entries |
| `songs/` | Paite hymn lyrics, with English titles and authors, and hymn-app snippets | 573 hymns, 846 snippets |
| `corrections.json` | Sentences that a native speaker checked and corrected | Grows over time |
| `grammar_notes.md` | Working notes on pronouns, verbs, and particles | Hypotheses, not a formal grammar |
| `paite_phrasebook.json` | Combined lookup file that the Levia assistant uses | 21,324 dictionary entries, 573 hymns |
| `eval/` | A small test of how well AI models know everyday Paite, with sentences checked by a native speaker | 16 sentences, growing |
| `prompts/everyday_en.txt` | Simple everyday English sentences for speakers to translate (public domain). Used by Paite Daily and Levia's practice | 199 sentences, growing |
| `scripts/` | The scripts that build `bible/laisiangthou/` and `training/` (MIT or Apache 2.0) | |

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

The same files are on Hugging Face at [LamkaLabs/paite-open-language-data](https://huggingface.co/datasets/LamkaLabs/paite-open-language-data), so you can load them without cloning this repository:

```python
from datasets import load_dataset

ds = load_dataset("LamkaLabs/paite-open-language-data", "parallel")["train"]
train = ds.filter(lambda r: r["split"] == "train")
test = ds.filter(lambda r: r["split"] == "test")
```

After you change any source file, rebuild the training files:

```bash
python scripts/build_training.py
```

## How well does AI know Paite?

`eval/everyday.jsonl` holds everyday sentences that a native speaker checked. `scripts/run_eval.py` asks any AI model to translate each one both ways and scores the answers with chrF (0 to 100, higher is better). Results go into [eval/RESULTS.md](eval/RESULTS.md).

```bash
python scripts/run_eval.py --base-url http://localhost:11434/v1 llama3.1
```

The command above tests a local model through Ollama. To test hosted models, set `EVAL_API_KEY` to an [OpenRouter](https://openrouter.ai) key and list model ids from openrouter.ai/models.

These sentences are always in the `test` split of `training/`, so a model trained on this repository is never trained on its own exam. The test set is small. Every sentence sent through the correction form can make it larger.

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
- Speech research: read-aloud recordings matched to checked text.
- Linguistic research on Paite morphology and particles.
- Evaluation sets for large language models on a low-resource language.

## Known limitations

- **Register.** Most sentences still come from the Bible and hymns, so formal and religious language is over-represented. The everyday pairs in `community/` are the fastest-growing correction to this; each is tagged as spoken, written or both.
- **Nine verses have no English.** The World English Bible omits or moves 9 verses that the Paite Bible keeps (for example, Acts 8:37, Luke 17:36, and Romans 16:25-27). These rows are in `monolingual.jsonl` only.
- **Dictionary quality.** The dictionary comes from an app. Some entries contain typing errors or several meanings in one string.
- **One fixed source error.** In the app database, Genesis 31:53 has the number 23. The import script corrects it.

## Sources and rights

This repository mixes original work and third-party text. The licence is different for each part. Read [LICENSE](LICENSE) before you redistribute the data.

| Part | Source | Rights |
|------|--------|--------|
| `corrections.json`, `grammar_notes.md`, `verified_*` entries, `eval/`, `glossary.json`, documentation | Maintainer and native-speaker contributors | CC BY 4.0 |
| `community/` | Paite Daily ([paite.lamkalabs.com](https://paite.lamkalabs.com/)) contributors, verified by reviewers | Per line, in its `licence` field: CC0 1.0 for answers sent before 21 Oct 2026, 18:47 UTC (954 lines), CC BY 4.0 after (451 lines on 16 Nov 2026). New lines are CC BY 4.0 |
| `audio/` | Paite Daily speakers, who agreed to publication before recording; accepted by a reviewer | CC BY 4.0 |
| `prompts/everyday_en.txt` | Written for this project | Public domain (CC0 1.0) |
| `scripts/`, `.github/` | Maintainer | MIT or Apache 2.0, your choice ([scripts/LICENSE-MIT](scripts/LICENSE-MIT), [scripts/LICENSE-APACHE](scripts/LICENSE-APACHE)) |
| Paite Bible in `bible/laisiangthou/` | Laisiangthou app (v5.0.2) by [John Samte](https://github.com/johnsamte) | Used with the permission of John Samte |
| English Bible text | World English Bible ([ebible.org](https://ebible.org/find/details.php?id=eng-web)) | Public domain |
| Paite Bible in `bible/legacy-etabetapi/` (retired) | Collected from etabetapi.com | Copyright of the original Paite Bible publisher |
| Dictionary | Extracted from the "Paite English Dictionary" Android app (v1.1.4) | Copyright of the app author |
| Hymn lyrics | Extracted from the "Kristian Labu" (v1.4.53) and "Biakna Labupi" (v1.0.0) Android apps | Copyright of the hymn authors, translators, and app publishers |
| UDHR example sentences | Universal Declaration of Human Rights, Paite translation | Public use permitted by the United Nations |

The third-party text is included for non-commercial research and language preservation. We do not claim ownership of it. If you own any of this text and want it removed or credited differently, open an issue. We will respond quickly.

## Credits

- **John Samte** ([github.com/johnsamte](https://github.com/johnsamte)) gave permission to use his Laisiangthou Bible, the primary Bible text in this repository.
- The Paite Daily contributors and reviewers, listed by name in [CONTRIBUTORS.md](CONTRIBUTORS.md).
- Native speakers who send corrections are credited in the git history.

## Contributing

Native speakers can help the most. See [CONTRIBUTING.md](CONTRIBUTING.md) to send a correction, a new phrase, or a grammar note.

## Citation

If you use this data in a paper, cite DOI [10.5281/zenodo.23349155](https://doi.org/10.5281/zenodo.23349155). It always points to the latest version (now v1.2.0, [10.5281/zenodo.24212533](https://doi.org/10.5281/zenodo.24212533)). The details are also in [CITATION.cff](CITATION.cff). GitHub shows a "Cite this repository" button for it.

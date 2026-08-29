# Paite Language Corpus

A working, owner-curated corpus for the Paite language (Tibeto-Burman, spoken in Manipur and Chin State). This is the neutral source of truth used by Levia, Claude, Codex, Kimi, and any future AI you point at it.

Repo: https://github.com/khooptong-sudo/paite-corpus

## What lives here

| File / folder | Contents |
|---------------|----------|
| `paite_phrasebook.json` | Master lookup: dictionary (21k+ entries), verified examples, owner corrections, songs, corpus examples |
| `parallel.txt` | Full English↔Paite Bible parallel text (66 books, 408 chapters, 10,471 verses) |
| `songs/` | Extracted Paite hymn/song lyrics |
| `[book]/` | One folder per Bible book (e.g. `Gen`, `Psa`, `Mat`) with tab-separated verse files |
| `corrections.json` | Audit trail of every owner correction, with timestamps and notes |

## How to use it

### From Levia

```powershell
# Store a correction you just learned
python -m levia --learn-paite "Na hon thei hia?" "Do you know me?"

# Or through chat / Telegram
"Levia, learn Paite: 'Ka dam e.' means 'I am well.'"
```

### From Python

```python
from levia.i18n.paite_feedback import add_correction, apply_corrections

add_correction("Hiai te bang chih didan a le?", "What are you doing?")
apply_corrections()
```

### From any AI assistant

Paste the context block from `F:/Vault the Brain/The Brain/wiki/Paite Language Resources.md` into the chat. The assistant will then reference these files instead of guessing.

## How corrections flow

1. You give Levia a correction (CLI, chat, or Telegram).
2. It is appended to `corrections.json` as an audit trail.
3. Verified corrections are merged into `paite_phrasebook.json` under `verified_corrections`.
4. Levia's translator checks `verified_corrections` first, before falling back to dictionary / corpus / LLM.
5. The corrected phrasebook is immediately available to all AIs reading `F:/Resources/paite_corpus/`.

## Contributing rules

- Only add corrections you are sure about.
- Use notes to mark uncertainty or dialect variation.
- Keep `paite_phrasebook.json` as the runtime source and `corrections.json` as the audit trail.
- If you turn this folder into a git repo, commit `corrections.json` and `paite_phrasebook.json` together.

## Sources

- Paite + English Dictionary APK (23k entries)
- Kristian Labu / Biakna Labupi song apps (1,400+ text snippets)
- World English Bible ↔ Paite parallel text from etabetapi.com
- Owner corrections and conversational examples

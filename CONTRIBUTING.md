# Contributing

Corrections from native Paite speakers make this data more useful than anything else. All help is welcome, from one word to a full grammar note.

## Ways to help

| You have | Do this |
|----------|---------|
| A wrong or missing translation | Fill in the [correction form](https://github.com/khooptong-sudo/paite-open-language-data/issues/new?template=correction.yml) |
| Several corrections | Send a pull request that edits `corrections.json` |
| A grammar observation | Send a pull request that edits `grammar_notes.md` |
| A source of Paite text that you have the right to share | Open an issue that names the source and its licence |

You do not need to know git. An issue is enough.

## Correction format

Add one object to the `corrections` list in `corrections.json`:

```json
{
  "paite": "Ka dam e.",
  "english": "I am well.",
  "incorrect": "Ka dam.",
  "register": "spoken",
  "notes": "Reply to 'how are you'",
  "status": "verified",
  "added_at": "2026-10-13T12:00:00+0530",
  "updated_at": "2026-10-13T12:00:00+0530"
}
```

- Set `status` to `verified` only if you are a fluent speaker and you are sure.
- Set `status` to `unverified` if you are not sure. A second speaker can then confirm it.
- `paite` is always the correct sentence.
- Add `incorrect` when you correct a wrong sentence (from a person, an app, or an AI). Each such entry becomes one row in `training/grammar.jsonl`. These rows teach a model to correct grammar, so they are the most valuable contribution.
- Set `register` to `spoken` or `written`. Leave it out if both are correct.
- Use `notes` for dialect differences, politeness level, or context.
- Use ISO 8601 timestamps with your time zone.

The maintainer copies verified corrections into `verified_corrections` in `paite_phrasebook.json`. Do not edit that key by hand in the same pull request.

## Rules

- Only add text that you wrote, or text with a licence that permits sharing. Do not paste copyrighted books, song lyrics, or app content.
- Keep files in UTF-8.
- One topic in each pull request.

By contributing, you agree that your contribution is released under CC BY 4.0 (see [LICENSE](LICENSE)).

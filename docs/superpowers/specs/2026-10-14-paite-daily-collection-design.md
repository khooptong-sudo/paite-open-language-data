# Paite Daily: community collection design

Date: 2026-10-14
Status: approved in conversation, awaiting written review

## Goal

Collect Paite translations of simple English sentences from the public, with the least possible effort for each person, and move verified translations into the open dataset automatically.

## Constraints

- Paite speakers use WhatsApp almost exclusively. Links are shared in WhatsApp groups. People do not sign up, and they drop off at every extra tap.
- Only fluent reviewers can mark a translation as correct. AI never verifies.
- No server for the owner to run. The workflow runs without the owner's computer.
- Contributors give no phone number or email. A name is optional.

## Decisions

| Topic | Decision |
|-------|----------|
| Platform | Cloudflare: one Worker with static assets, a D1 database, Cron Triggers, Turnstile, and Cloudflare Access |
| Address | `paite.lamkalabs.com` (contributors), `paite.lamkalabs.com/review` (reviewers) |
| Contributor licence | CC0 1.0. Shown under the Send button. Allows later use in Mozilla Common Voice |
| UI language | Paite first, with small English below |
| Register | Contributors choose Spoken / Written / Both. Default: Both |
| AI provider | DeepSeek API (`deepseek-chat`), advisory only |
| Answers per sentence | 2, then the sentence leaves the pool until review |
| Code location | New public repository `khooptong-sudo/paite-daily`. The dataset stays in `paite-open-language-data` |

## 1. Contributor experience

1. The link opens straight onto a sentence card. There is no sign-up and no splash screen.
2. The card shows the English sentence, one text box for Paite, a Spoken / Written / Both choice, and two buttons: Send and Skip.
3. After Send or Skip, the next card appears at once.
4. The server gives each phone only sentences that have fewer than 2 answers and that this phone has not seen.
5. After the first answer, the page asks once: "Want your name on the Paite contributors list?" The answer is stored on the phone.
6. The page shows a small "today" count and a thank-you after 5 answers. It never shows the size of the pool.
7. Turnstile (invisible) and a rate limit per phone block spam.

Phone identity: a random ID created in the browser and kept in local storage. It is not linked to a person.

## 2. Reviewer experience

1. Cloudflare Access protects `/review`. Reviewers sign in with a one-time code sent to their email. The allowed emails are an Access policy list.
2. The Worker also checks the Access JWT on every review request.
3. Each card shows the English sentence, all answers side by side with contributor names, and the DeepSeek note.
4. Actions: Accept an answer, Fix (edit, then accept), Reject all (the sentence returns to the pool), Retire sentence (bad English). The reviewer can set the register and add a note. The reviewer can mark a second answer as "also correct".
5. Order: answers that agree, then disagreements, then items flagged as junk.
6. A sentence is locked for 10 minutes while one reviewer has it open.
7. Reviewer display names come from a Worker variable `REVIEWERS` (JSON map of email to display name). Emails are never published.
8. Every decision goes into a review log with reviewer email, time, and result. The owner can undo a decision.

## 3. Automation

Cron Triggers in the same Worker:

| Schedule | Job | Uses DeepSeek |
|----------|-----|---------------|
| Every 15 minutes | Pre-review: write an advisory note for each new answer (agreement, Tedim/Bible style markers such as `nong`, `hiam`, `zong`, final `hi`; English instead of Paite; junk) | Yes |
| Daily 02:00 UTC | Refill: when fewer than 300 sentences are open, ask for 50 new simple sentences on a rotating topic; drop duplicates by normalised text | Yes |
| Daily 03:00 UTC | Export: commit new verified rows as one new file `community/verified-<first review id>-<last review id>.jsonl` in the dataset repository (a rerun cannot duplicate rows); read `corrections.json` and retire sentences the owner already translated | No |

Failure handling:

- DeepSeek failure: answers have no note. Collection and review continue.
- Export failure: retry on the next run. D1 is the record, so nothing is lost.
- Every job run is logged in a `job_runs` table. Layer 2 adds an email to the owner after two failures in a row of the same job, through Cloudflare Email Routing (`send_email` binding to the owner's verified address).

Secrets (the owner sets them with `wrangler secret put`; Claude never sees them): `DEEPSEEK_API_KEY`, `GITHUB_TOKEN` (fine-grained, contents write on `paite-open-language-data` only), `TURNSTILE_SECRET`.

## 4. Data model (D1)

| Table | Columns |
|-------|---------|
| `sentences` | `id`, `english` (unique, normalised), `source` (`prompts`, `deepseek`), `status` (`open`, `full`, `verified`, `retired`), `answer_count`, `created_at` |
| `answers` | `id`, `sentence_id`, `paite`, `register`, `phone_id`, `contributor_name`, `ai_note`, `ai_flag`, `status` (`new`, `accepted`, `also_correct`, `rejected`), `created_at` |
| `seen` | `phone_id`, `sentence_id`, `action` (`answered`, `skipped`), `created_at` |
| `reviews` | `id`, `sentence_id`, `reviewer_email`, `decision`, `accepted_answer_id`, `final_paite`, `register`, `note`, `created_at`, `undone_at` |
| `locks` | `sentence_id`, `reviewer_email`, `expires_at` |
| `exports` | `id`, `first_review_id`, `last_review_id`, `path`, `created_at` |
| `job_runs` | `id`, `job`, `ok`, `detail`, `created_at` |

Assignment query: pick an `open` sentence with `answer_count < 2` that has no `seen` row for this phone, in random order. On the second answer, set `status = full`. On "Reject all", set `status = open` and `answer_count = 0`.

## 5. Into the dataset

- `community/verified-<first>-<last>.jsonl` files, one line per verified sentence: `id`, `english`, `paite`, `register`, `contributor`, `verified_by` (reviewer display name, not email), `verified_at`, `licence: "CC0-1.0"`, plus `also_correct` variants.
- `scripts/build_training.py` reads it as source `community`.
- `CONTRIBUTORS.md` is regenerated by the export job: named contributors and reviewers with counts.
- LICENSE gains a CC0 section for `community/`.
- The GitHub Pages `daily/` page redirects to `paite.lamkalabs.com`.
- The Google Form stays as the "report a wrong sentence" channel. Levia practice is unchanged.

## 6. Testing

- Worker unit tests (Vitest with the Cloudflare Workers pool): assignment never returns a full or seen sentence; the second answer closes a sentence; reject-all reopens it; non-reviewer requests to `/review` APIs are refused; rate limit holds; export writes valid JSON lines.
- The dataset repository's existing GitHub check validates the `community/` files and the training rebuild.
- Launch check: the owner and one reviewer answer 5 sentences, review 5, and confirm the export commit the next day.

## 7. Rollout

1. Core: contributor page, D1, review page with Access, nightly export, redirect.
2. DeepSeek: pre-review notes and daily refill.
3. Delight: Share to WhatsApp Status image, contributors page, then badges and rankings for contributors and reviewers.

Each layer works end to end before the next starts.

## 8. Needed from the owner

- `wrangler login` in a terminal, so the Worker can be deployed to the Lamka Labs Cloudflare account.
- Cloudflare Zero Trust team name (free plan) for Access, created once in the dashboard.
- Reviewer email addresses.
- Paite text for these UI strings:
  1. Translate into Paite
  2. Send
  3. Skip
  4. Spoken / Written / Both
  5. Thank you!
  6. today
  7. Want your name on the Paite contributors list?
  8. Your name
  9. No thanks
  10. Your translations are given to everyone, free (public domain)
  11. Loading the next sentence…
  12. No more sentences right now. Come back tomorrow.
  13. Could not send. Check your internet and try again.
  14. Share on WhatsApp Status
  15. I helped write Paite into the future

## Out of scope

- WhatsApp Business API bots and paid pushes.
- Voice recording (a later Common Voice project).
- Automatic verification of any kind.

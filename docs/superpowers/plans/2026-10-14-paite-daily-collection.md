# Paite Daily Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Cloudflare app at `paite.lamkalabs.com` where anyone translates simple English sentences into Paite with no sign-up, reviewers verify the answers, and verified sentences flow into the open dataset every night.

**Architecture:** One Cloudflare Worker serves static pages from `public/` and a small JSON API. D1 stores sentences, answers, review decisions and export history. Cloudflare Access guards `/review`. A nightly Cron Trigger commits verified rows to the dataset repository through the GitHub contents API. All outside services (Turnstile, Access JWT check, GitHub) sit behind injected functions, so the tests run with no network.

**Tech Stack:** TypeScript, Cloudflare Workers + Static Assets, D1, Cron Triggers, Turnstile, Cloudflare Access, `jose` (JWT), Vitest with `@cloudflare/vitest-pool-workers`, Wrangler. Plain HTML/JS for the two pages (no framework).

**Spec:** `docs/superpowers/specs/2026-10-14-paite-daily-collection-design.md` (in `khooptong-sudo/paite-open-language-data`).

## Global Constraints

- App repository: new public repo `khooptong-sudo/paite-daily`, local path `F:\Resources\paite-daily`.
- Address: `paite.lamkalabs.com` (contributors), `paite.lamkalabs.com/review` (reviewers).
- Answers per sentence: 2, then `status = full` until review.
- A phone never receives a sentence it answered or skipped.
- Contributors give no phone number or email. Name is optional, at most 60 characters.
- Paite answer: 1 to 300 characters after trimming. Register: `spoken`, `written` or `both` (default `both`).
- Contributor licence: CC0 1.0, shown under the Send button. Exported rows carry `"licence": "CC0-1.0"`.
- AI never verifies. Only a signed-in reviewer can set `status = verified`.
- Reviewer emails are never published. Display names come from the `REVIEWERS` variable (JSON map email → name).
- Secrets are set by the owner with `wrangler secret put`. No secret appears in the repository or in chat.
- Rate limit: at most 10 answers per phone per minute.
- Review lock: 10 minutes.
- UI language: Paite first, small English below, from `public/strings.js`. Until the owner supplies a Paite string, the page shows the English string only.
- Commits: no `Co-Authored-By` trailer, no "Generated with" line.

## Review Focus

1. Two contributors submit the second answer to the same sentence at the same moment: exactly one is accepted, the other gets "already full" and receives a new sentence, and `answer_count` never exceeds 2. (Task 3, test `second answer race`.)
2. The open pool runs dry: the page shows "No more sentences right now. Come back tomorrow." instead of an error or an empty card. (Task 2 test `empty pool returns 204`; Task 4 handles 204.)
3. A reviewer's lock expires and a second reviewer decides first: the first reviewer's decision is refused with 409 and the page loads the next card, with no double verification. (Task 5, test `expired lock is refused`.)
4. Unusual Paite input: leading or trailing spaces, line breaks, very long text, control characters, combining accents. Text is NFC-normalised and trimmed, inner whitespace collapsed, and anything over 300 characters or containing control characters is refused with a clear message. (Task 3, test `answer text is cleaned and bounded`.)
5. The nightly export crashes after GitHub saved the file but before D1 recorded it: the rerun writes nothing twice. (Task 7, test `rerun after partial export does not duplicate`.)

---

## File Structure (repo `paite-daily`)

| Path | Responsibility |
|------|----------------|
| `wrangler.jsonc` | Worker, assets, D1 binding, cron, custom domain, plain variables |
| `package.json`, `tsconfig.json`, `vitest.config.ts` | Tooling |
| `migrations/0001_init.sql` | D1 schema |
| `src/types.ts` | `Env`, `Deps`, `json()` helper |
| `src/text.ts` | Input cleaning and English normalisation |
| `src/session.ts` | Signed session token (HMAC) |
| `src/turnstile.ts` | Turnstile server check |
| `src/access.ts` | Cloudflare Access JWT check |
| `src/db.ts` | All contributor-side SQL |
| `src/reviewdb.ts` | All reviewer-side SQL |
| `src/contributor.ts` | `/api/*` routes |
| `src/review.ts` | `/review/api/*` routes |
| `src/export.ts` | Nightly export and owner-translation retirement |
| `src/index.ts` | Wiring: router, `createApp`, `scheduled` |
| `public/index.html`, `public/app.js`, `public/strings.js`, `public/style.css` | Contributor page |
| `public/review/index.html`, `public/review/review.js` | Reviewer page |
| `scripts/seed.mjs` | Build `seed.sql` from `prompts/everyday_en.txt` |
| `test/*.test.ts` | Vitest tests in the Workers runtime |

Dataset repo (`paite-open-language-data`) changes in Task 8: `scripts/build_training.py`, `LICENSE`, `daily/index.html`, `README.md`.

---

## Layer 1: Core

### Task 1: Project scaffold, schema, test harness

**Files:**
- Create: `wrangler.jsonc`, `package.json`, `tsconfig.json`, `vitest.config.ts`, `migrations/0001_init.sql`, `src/types.ts`, `test/apply-migrations.ts`, `test/env.d.ts`, `test/schema.test.ts`, `.gitignore`

**Interfaces:**
- Produces: `Env`, `Deps`, `json(data, status?)` in `src/types.ts`; D1 tables `sentences`, `answers`, `seen`, `reviews`, `locks`, `exports`, `job_runs`.

- [ ] **Step 1: Create the repo and install tools**

```bash
mkdir F:/Resources/paite-daily && cd F:/Resources/paite-daily && git init -b main
npm init -y
npm install -D wrangler typescript @cloudflare/workers-types @cloudflare/vitest-pool-workers
npm install jose
```

Then read the `vitest` peer dependency of the installed pool and install that exact range:

```bash
node -e "console.log(require('@cloudflare/vitest-pool-workers/package.json').peerDependencies.vitest)"
npm install -D "vitest@<range printed above>"
```

- [ ] **Step 2: Write `wrangler.jsonc`**

```jsonc
{
  "name": "paite-daily",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-01",
  "assets": { "directory": "./public", "binding": "ASSETS", "run_worker_first": ["/api/*", "/review/api/*"] },
  "d1_databases": [
    { "binding": "DB", "database_name": "paite-daily", "database_id": "00000000-0000-0000-0000-000000000000", "migrations_dir": "migrations" }
  ],
  "triggers": { "crons": ["0 3 * * *"] },
  "vars": {
    "ACCESS_TEAM_DOMAIN": "",
    "ACCESS_AUD": "",
    "TURNSTILE_SITE_KEY": "",
    "REVIEWERS": "{}",
    "OWNER_EMAIL": "",
    "CORPUS_REPO": "khooptong-sudo/paite-open-language-data",
    "CORPUS_BRANCH": "master"
  }
}
```

The all-zero `database_id` is valid for local tests. Task 8 replaces it with the real id.

- [ ] **Step 3: Write `package.json` scripts, `tsconfig.json`, `.gitignore`**

Add to `package.json`:

```json
"scripts": {
  "test": "vitest run",
  "typecheck": "tsc --noEmit",
  "deploy": "wrangler deploy"
}
```

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "es2022", "module": "es2022", "moduleResolution": "bundler",
    "lib": ["es2022"], "strict": true, "noEmit": true, "skipLibCheck": true,
    "types": ["@cloudflare/workers-types", "@cloudflare/vitest-pool-workers"]
  },
  "include": ["src", "test"]
}
```

`.gitignore`:

```
node_modules/
.wrangler/
seed.sql
.dev.vars
```

- [ ] **Step 4: Write the schema `migrations/0001_init.sql`**

```sql
CREATE TABLE sentences (
  id INTEGER PRIMARY KEY,
  english TEXT NOT NULL,
  english_key TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'full', 'verified', 'retired')),
  answer_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX sentences_pool ON sentences (status, answer_count);

CREATE TABLE answers (
  id INTEGER PRIMARY KEY,
  sentence_id INTEGER NOT NULL REFERENCES sentences (id),
  paite TEXT NOT NULL,
  register TEXT NOT NULL CHECK (register IN ('spoken', 'written', 'both')),
  phone_id TEXT NOT NULL,
  contributor_name TEXT,
  ai_note TEXT,
  ai_flag TEXT,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'accepted', 'also_correct', 'rejected')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX answers_by_phone_time ON answers (phone_id, created_at);
CREATE INDEX answers_by_sentence ON answers (sentence_id, status);

CREATE TABLE seen (
  phone_id TEXT NOT NULL,
  sentence_id INTEGER NOT NULL REFERENCES sentences (id),
  action TEXT NOT NULL CHECK (action IN ('answered', 'skipped')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (phone_id, sentence_id)
);

CREATE TABLE reviews (
  id INTEGER PRIMARY KEY,
  sentence_id INTEGER NOT NULL REFERENCES sentences (id),
  reviewer_email TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('accept', 'reject', 'retire')),
  accepted_answer_id INTEGER REFERENCES answers (id),
  final_paite TEXT,
  register TEXT,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  undone_at TEXT
);

CREATE TABLE locks (
  sentence_id INTEGER PRIMARY KEY REFERENCES sentences (id),
  reviewer_email TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE TABLE exports (
  id INTEGER PRIMARY KEY,
  first_review_id INTEGER NOT NULL,
  last_review_id INTEGER NOT NULL,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE job_runs (
  id INTEGER PRIMARY KEY,
  job TEXT NOT NULL,
  ok INTEGER NOT NULL,
  detail TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

- [ ] **Step 5: Write `src/types.ts`**

```ts
export interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  TURNSTILE_SECRET: string;
  SESSION_SECRET: string;
  GITHUB_TOKEN: string;
  ACCESS_TEAM_DOMAIN: string;
  ACCESS_AUD: string;
  TURNSTILE_SITE_KEY: string;
  REVIEWERS: string;
  OWNER_EMAIL: string;
  CORPUS_REPO: string;
  CORPUS_BRANCH: string;
}

export interface Deps {
  verifyTurnstile(token: string, ip: string | null, env: Env): Promise<boolean>;
  verifyAccess(req: Request, env: Env): Promise<string | null>;
  now(): number;
}

export function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}
```

- [ ] **Step 6: Write the test harness**

`vitest.config.ts`:

```ts
import { defineWorkersConfig, readD1Migrations } from "@cloudflare/vitest-pool-workers/config";

export default defineWorkersConfig(async () => {
  const migrations = await readD1Migrations("./migrations");
  return {
    test: {
      setupFiles: ["./test/apply-migrations.ts"],
      poolOptions: {
        workers: {
          wrangler: { configPath: "./wrangler.jsonc" },
          miniflare: {
            bindings: {
              TEST_MIGRATIONS: migrations,
              SESSION_SECRET: "test-session-secret",
              TURNSTILE_SECRET: "unused-in-tests",
              GITHUB_TOKEN: "test-github-token",
              REVIEWERS: JSON.stringify({ "rev@example.org": "Rev One", "owner@example.org": "Owner" }),
              OWNER_EMAIL: "owner@example.org",
            },
          },
        },
      },
    },
  };
});
```

`test/apply-migrations.ts`:

```ts
import { applyD1Migrations, env } from "cloudflare:test";
await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
```

`test/env.d.ts`:

```ts
declare module "cloudflare:test" {
  interface ProvidedEnv extends import("../src/types").Env {
    TEST_MIGRATIONS: D1Migration[];
  }
}
```

- [ ] **Step 7: Write the failing schema test `test/schema.test.ts`**

```ts
import { env } from "cloudflare:test";
import { expect, it } from "vitest";

it("creates every table", async () => {
  const { results } = await env.DB.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").all<{ name: string }>();
  const names = results.map((r) => r.name);
  for (const t of ["answers", "exports", "job_runs", "locks", "reviews", "seen", "sentences"]) expect(names).toContain(t);
});

it("rejects an unknown sentence status", async () => {
  await expect(
    env.DB.prepare("INSERT INTO sentences (english, english_key, source, status) VALUES ('a', 'a', 'x', 'bogus')").run(),
  ).rejects.toThrow();
});
```

- [ ] **Step 8: Run the tests**

Run: `npx vitest run test/schema.test.ts`
Expected: 2 passed. (If the migration file is missing, the first test fails with "expected [...] to contain 'answers'".)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Scaffold Worker, D1 schema, and test harness"
```

---

### Task 2: Sessions, sentence assignment, skip

**Files:**
- Create: `src/text.ts`, `src/session.ts`, `src/db.ts`, `src/contributor.ts`, `src/index.ts`, `test/helpers.ts`, `test/assign.test.ts`

**Interfaces:**
- Consumes: `Env`, `Deps`, `json` (Task 1).
- Produces:
  - `normaliseEnglish(s: string): string`
  - `cleanText(s: unknown, max: number): string | null`
  - `isPhoneId(s: unknown): s is string`
  - `signSession(phoneId: string, expiresAt: number, secret: string): Promise<string>`
  - `readSession(token: string | null, now: number, secret: string): Promise<string | null>`
  - `nextSentence(db: D1Database, phoneId: string): Promise<{ id: number; english: string } | null>`
  - `skipSentence(db: D1Database, phoneId: string, sentenceId: number): Promise<void>`
  - `handleContributor(req: Request, env: Env, deps: Deps): Promise<Response>`
  - `createApp(deps: Deps): (req: Request, env: Env) => Promise<Response>`
  - Test helpers: `fakeDeps(overrides?)`, `addSentences(...english: string[])`, `session(phoneId)`, `PHONE_A`, `PHONE_B`, `PHONE_C`.

- [ ] **Step 1: Write `src/text.ts`**

```ts
const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;

export function normaliseEnglish(s: string): string {
  return s.normalize("NFC").trim().replace(/\s+/g, " ").toLowerCase();
}

/** NFC, trimmed, inner whitespace collapsed; null if empty, too long, or containing control characters. */
export function cleanText(s: unknown, max: number): string | null {
  if (typeof s !== "string" || CONTROL.test(s)) return null;
  const t = s.normalize("NFC").trim().replace(/\s+/g, " ");
  return t.length >= 1 && t.length <= max ? t : null;
}

export function isPhoneId(s: unknown): s is string {
  return typeof s === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
}
```

- [ ] **Step 2: Write `src/session.ts`**

```ts
const enc = new TextEncoder();

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
}

function b64url(buf: ArrayBuffer): string {
  let bin = "";
  for (const b of new Uint8Array(buf)) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function signSession(phoneId: string, expiresAt: number, secret: string): Promise<string> {
  const body = `${phoneId}.${expiresAt}`;
  const sig = await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(body));
  return `${body}.${b64url(sig)}`;
}

export async function readSession(token: string | null, now: number, secret: string): Promise<string | null> {
  if (!token) return null;
  const [phoneId, exp, sig] = token.split(".");
  if (!phoneId || !exp || !sig || !(Number(exp) > now)) return null;
  const expected = await signSession(phoneId, Number(exp), secret);
  if (expected.length !== token.length) return null;
  let diff = 0;
  for (let i = 0; i < token.length; i++) diff |= expected.charCodeAt(i) ^ token.charCodeAt(i);
  return diff === 0 ? phoneId : null;
}
```

- [ ] **Step 3: Write `src/db.ts` (assignment and skip only)**

```ts
export async function nextSentence(db: D1Database, phoneId: string): Promise<{ id: number; english: string } | null> {
  return db
    .prepare(
      `SELECT s.id, s.english FROM sentences s
       WHERE s.status = 'open' AND s.answer_count < 2
         AND NOT EXISTS (SELECT 1 FROM seen WHERE seen.phone_id = ?1 AND seen.sentence_id = s.id)
       ORDER BY random() LIMIT 1`,
    )
    .bind(phoneId)
    .first<{ id: number; english: string }>();
}

export async function skipSentence(db: D1Database, phoneId: string, sentenceId: number): Promise<void> {
  await db.prepare("INSERT OR IGNORE INTO seen (phone_id, sentence_id, action) VALUES (?1, ?2, 'skipped')").bind(phoneId, sentenceId).run();
}
```

- [ ] **Step 4: Write `src/contributor.ts` (session, next, skip)**

```ts
import { nextSentence, skipSentence } from "./db";
import { readSession, signSession } from "./session";
import { isPhoneId } from "./text";
import { json, type Deps, type Env } from "./types";

const DAY_MS = 86_400_000;

async function body(req: Request): Promise<Record<string, unknown>> {
  try {
    const b = await req.json();
    return b && typeof b === "object" ? (b as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export async function handleContributor(req: Request, env: Env, deps: Deps): Promise<Response> {
  const { pathname } = new URL(req.url);

  if (pathname === "/api/session" && req.method === "POST") {
    const b = await body(req);
    if (!isPhoneId(b.phoneId) || typeof b.turnstileToken !== "string") return json({ error: "bad_request" }, 400);
    const ok = await deps.verifyTurnstile(b.turnstileToken, req.headers.get("CF-Connecting-IP"), env);
    if (!ok) return json({ error: "turnstile_failed" }, 403);
    return json({ session: await signSession(b.phoneId, deps.now() + DAY_MS, env.SESSION_SECRET) });
  }

  const phoneId = await readSession(req.headers.get("X-Session"), deps.now(), env.SESSION_SECRET);
  if (!phoneId) return json({ error: "no_session" }, 401);

  if (pathname === "/api/next" && req.method === "GET") {
    const s = await nextSentence(env.DB, phoneId);
    return s ? json(s) : new Response(null, { status: 204 });
  }

  if (pathname === "/api/skip" && req.method === "POST") {
    const b = await body(req);
    if (!Number.isInteger(b.sentenceId)) return json({ error: "bad_request" }, 400);
    await skipSentence(env.DB, phoneId, b.sentenceId as number);
    return json({ ok: true });
  }

  return json({ error: "not_found" }, 404);
}
```

- [ ] **Step 5: Write `src/index.ts`**

```ts
import { handleContributor } from "./contributor";
import type { Deps, Env } from "./types";

export function createApp(deps: Deps) {
  return async (req: Request, env: Env): Promise<Response> => {
    const { pathname } = new URL(req.url);
    if (pathname.startsWith("/api/")) return handleContributor(req, env, deps);
    return env.ASSETS.fetch(req);
  };
}
```

(The default export is added in Task 3, when the real Turnstile check exists.)

- [ ] **Step 6: Write `test/helpers.ts`**

```ts
import { env } from "cloudflare:test";
import { createApp } from "../src/index";
import { signSession } from "../src/session";
import { normaliseEnglish } from "../src/text";
import type { Deps } from "../src/types";

export const PHONE_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const PHONE_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
export const PHONE_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
export const NOW = 1_800_000_000_000;

export function fakeDeps(overrides: Partial<Deps> = {}): Deps {
  return {
    verifyTurnstile: async () => true,
    verifyAccess: async () => null,
    now: () => NOW,
    ...overrides,
  };
}

export async function addSentences(...english: string[]): Promise<number[]> {
  const ids: number[] = [];
  for (const e of english) {
    const r = await env.DB.prepare("INSERT INTO sentences (english, english_key, source) VALUES (?1, ?2, 'test') RETURNING id")
      .bind(e, normaliseEnglish(e))
      .first<{ id: number }>();
    ids.push(r!.id);
  }
  return ids;
}

export function session(phoneId: string): Promise<string> {
  return signSession(phoneId, NOW + 3_600_000, env.SESSION_SECRET);
}

export async function call(path: string, init: RequestInit & { session?: string } = {}, deps = fakeDeps()) {
  const headers = new Headers(init.headers);
  if (init.session) headers.set("X-Session", init.session);
  if (init.body) headers.set("content-type", "application/json");
  return createApp(deps)(new Request(`https://paite.lamkalabs.com${path}`, { ...init, headers }), env);
}
```

- [ ] **Step 7: Write the failing tests `test/assign.test.ts`**

```ts
import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { readSession, signSession } from "../src/session";
import { addSentences, call, fakeDeps, NOW, PHONE_A, session } from "./helpers";

describe("session", () => {
  it("issues a session after Turnstile passes", async () => {
    const r = await call("/api/session", { method: "POST", body: JSON.stringify({ phoneId: PHONE_A, turnstileToken: "t" }) });
    expect(r.status).toBe(200);
    const { session: token } = await r.json<{ session: string }>();
    expect(await readSession(token, NOW, env.SESSION_SECRET)).toBe(PHONE_A);
  });

  it("refuses a session when Turnstile fails", async () => {
    const deps = fakeDeps({ verifyTurnstile: async () => false });
    const r = await call("/api/session", { method: "POST", body: JSON.stringify({ phoneId: PHONE_A, turnstileToken: "t" }) }, deps);
    expect(r.status).toBe(403);
  });

  it("rejects a tampered or expired session", async () => {
    const good = await signSession(PHONE_A, NOW + 1000, env.SESSION_SECRET);
    expect(await readSession(good.slice(0, -2) + "xx", NOW, env.SESSION_SECRET)).toBeNull();
    expect(await readSession(good, NOW + 2000, env.SESSION_SECRET)).toBeNull();
    expect((await call("/api/next")).status).toBe(401);
  });
});

describe("assignment", () => {
  it("empty pool returns 204", async () => {
    const r = await call("/api/next", { session: await session(PHONE_A) });
    expect(r.status).toBe(204);
  });

  it("never returns a skipped sentence to the same phone", async () => {
    const [a, b] = await addSentences("Good morning.", "I am hungry.");
    const s = await session(PHONE_A);
    await call("/api/skip", { method: "POST", session: s, body: JSON.stringify({ sentenceId: a }) });
    for (let i = 0; i < 10; i++) {
      const r = await call("/api/next", { session: s });
      expect((await r.json<{ id: number }>()).id).toBe(b);
    }
  });

  it("never returns a full, verified or retired sentence", async () => {
    const [full, verified, retired, open] = await addSentences("One.", "Two.", "Three.", "Four.");
    await env.DB.batch([
      env.DB.prepare("UPDATE sentences SET status = 'full', answer_count = 2 WHERE id = ?1").bind(full),
      env.DB.prepare("UPDATE sentences SET status = 'verified' WHERE id = ?1").bind(verified),
      env.DB.prepare("UPDATE sentences SET status = 'retired' WHERE id = ?1").bind(retired),
    ]);
    const s = await session(PHONE_A);
    for (let i = 0; i < 10; i++) {
      expect((await (await call("/api/next", { session: s })).json<{ id: number }>()).id).toBe(open);
    }
  });
});
```

- [ ] **Step 8: Run the tests and check they fail, then pass**

Run before Steps 1-5 exist (or with `src/db.ts` empty): `npx vitest run test/assign.test.ts`
Expected: FAIL, import errors.
Run after Steps 1-6: `npx vitest run test/assign.test.ts`
Expected: 6 passed.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Contributor sessions, sentence assignment, and skip"
```

---

### Task 3: Answer submission, rate limit, Turnstile check

**Files:**
- Modify: `src/db.ts` (add `recordAnswer`, `answersInLastMinute`), `src/contributor.ts` (add `/api/answer`), `src/index.ts` (default export)
- Create: `src/turnstile.ts`, `test/answer.test.ts`, `test/turnstile.test.ts`

**Interfaces:**
- Consumes: Task 2 helpers and functions.
- Produces:
  - `recordAnswer(db: D1Database, a: { phoneId: string; sentenceId: number; paite: string; register: Register; name: string | null }): Promise<"ok" | "closed">`
  - `answersInLastMinute(db: D1Database, phoneId: string): Promise<number>`
  - `type Register = "spoken" | "written" | "both"`
  - `verifyTurnstile(token: string, ip: string | null, env: Env, fetcher?: typeof fetch): Promise<boolean>`
  - Default export `{ fetch, scheduled }` in `src/index.ts` (scheduled added in Task 7).

- [ ] **Step 1: Write the failing tests `test/answer.test.ts`**

```ts
import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { addSentences, call, PHONE_A, PHONE_B, PHONE_C, session } from "./helpers";

const answer = async (phone: string, sentenceId: number, paite = "Ka dam e.", extra: Record<string, unknown> = {}) =>
  call("/api/answer", {
    method: "POST",
    session: await session(phone),
    body: JSON.stringify({ sentenceId, paite, register: "both", ...extra }),
  });

describe("answers", () => {
  it("records an answer and hides the sentence from that phone", async () => {
    const [id] = await addSentences("I am well.");
    expect((await answer(PHONE_A, id)).status).toBe(200);
    expect((await call("/api/next", { session: await session(PHONE_A) })).status).toBe(204);
    const row = await env.DB.prepare("SELECT paite, register, status FROM answers WHERE sentence_id = ?1").bind(id).first();
    expect(row).toEqual({ paite: "Ka dam e.", register: "both", status: "new" });
  });

  it("second answer closes the sentence", async () => {
    const [id] = await addSentences("I am well.");
    await answer(PHONE_A, id);
    await answer(PHONE_B, id);
    const s = await env.DB.prepare("SELECT status, answer_count FROM sentences WHERE id = ?1").bind(id).first();
    expect(s).toEqual({ status: "full", answer_count: 2 });
    expect((await call("/api/next", { session: await session(PHONE_C) })).status).toBe(204);
    expect((await answer(PHONE_C, id)).status).toBe(409);
  });

  it("second answer race: never more than 2 answers", async () => {
    const [id] = await addSentences("I am well.");
    await answer(PHONE_A, id);
    const results = await Promise.all([answer(PHONE_B, id), answer(PHONE_C, id)]);
    expect(results.map((r) => r.status).sort()).toEqual([200, 409]);
    const { n } = (await env.DB.prepare("SELECT count(*) AS n FROM answers WHERE sentence_id = ?1").bind(id).first<{ n: number }>())!;
    expect(n).toBe(2);
  });

  it("the same phone cannot answer the same sentence twice", async () => {
    const [id] = await addSentences("I am well.");
    expect((await answer(PHONE_A, id)).status).toBe(200);
    expect((await answer(PHONE_A, id)).status).toBe(409);
  });

  it("answer text is cleaned and bounded", async () => {
    const [a, b, c, d] = await addSentences("One.", "Two.", "Three.", "Four.");
    expect((await answer(PHONE_A, a, "  Ka   dam\n e.  ")).status).toBe(200);
    const row = await env.DB.prepare("SELECT paite FROM answers WHERE sentence_id = ?1").bind(a).first<{ paite: string }>();
    expect(row!.paite).toBe("Ka dam e.");
    expect((await answer(PHONE_A, b, "x".repeat(301))).status).toBe(400);
    expect((await answer(PHONE_A, c, "bad\u0007bell")).status).toBe(400);
    expect((await answer(PHONE_A, d, "   ")).status).toBe(400);
  });

  it("rejects a bad register and keeps an optional name", async () => {
    const [a, b] = await addSentences("One.", "Two.");
    expect((await answer(PHONE_A, a, "Ka dam e.", { register: "sung" })).status).toBe(400);
    expect((await answer(PHONE_A, b, "Ka dam e.", { register: "spoken", name: "  Mang  " })).status).toBe(200);
    const row = await env.DB.prepare("SELECT register, contributor_name FROM answers WHERE sentence_id = ?1").bind(b).first();
    expect(row).toEqual({ register: "spoken", contributor_name: "Mang" });
  });

  it("rate limit: the 11th answer within a minute is refused", async () => {
    const ids = await addSentences(...Array.from({ length: 11 }, (_, i) => `Sentence ${i}.`));
    for (const id of ids.slice(0, 10)) expect((await answer(PHONE_A, id)).status).toBe(200);
    expect((await answer(PHONE_A, ids[10])).status).toBe(429);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/answer.test.ts`
Expected: FAIL, `/api/answer` returns 404.

- [ ] **Step 3: Add to `src/db.ts`**

```ts
export type Register = "spoken" | "written" | "both";

export async function answersInLastMinute(db: D1Database, phoneId: string): Promise<number> {
  const r = await db
    .prepare("SELECT count(*) AS n FROM answers WHERE phone_id = ?1 AND created_at > datetime('now', '-60 seconds')")
    .bind(phoneId)
    .first<{ n: number }>();
  return r?.n ?? 0;
}

/**
 * Claims a slot with one conditional UPDATE, so two simultaneous second answers
 * cannot both succeed. Only the winner inserts its answer.
 */
export async function recordAnswer(
  db: D1Database,
  a: { phoneId: string; sentenceId: number; paite: string; register: Register; name: string | null },
): Promise<"ok" | "closed"> {
  const claim = await db
    .prepare(
      `UPDATE sentences
         SET answer_count = answer_count + 1,
             status = CASE WHEN answer_count + 1 >= 2 THEN 'full' ELSE status END
       WHERE id = ?1 AND status = 'open' AND answer_count < 2
         AND NOT EXISTS (SELECT 1 FROM seen WHERE phone_id = ?2 AND sentence_id = ?1)`,
    )
    .bind(a.sentenceId, a.phoneId)
    .run();
  if (claim.meta.changes !== 1) return "closed";
  try {
    await db.batch([
      db.prepare("INSERT INTO answers (sentence_id, paite, register, phone_id, contributor_name) VALUES (?1, ?2, ?3, ?4, ?5)")
        .bind(a.sentenceId, a.paite, a.register, a.phoneId, a.name),
      db.prepare("INSERT INTO seen (phone_id, sentence_id, action) VALUES (?1, ?2, 'answered')").bind(a.phoneId, a.sentenceId),
    ]);
  } catch (e) {
    await db
      .prepare("UPDATE sentences SET answer_count = answer_count - 1, status = 'open' WHERE id = ?1 AND status IN ('open', 'full')")
      .bind(a.sentenceId)
      .run();
    throw e;
  }
  return "ok";
}
```

- [ ] **Step 4: Add the `/api/answer` route to `src/contributor.ts`**

Add imports `recordAnswer`, `answersInLastMinute`, `type Register` from `./db` and `cleanText` from `./text`. Insert before the final `return json({ error: "not_found" }, 404);`:

```ts
  if (pathname === "/api/answer" && req.method === "POST") {
    const b = await body(req);
    const paite = cleanText(b.paite, 300);
    const register = (b.register ?? "both") as Register;
    const name = b.name === undefined || b.name === "" ? null : cleanText(b.name, 60);
    if (!Number.isInteger(b.sentenceId) || !paite || !["spoken", "written", "both"].includes(register) || (b.name && !name)) {
      return json({ error: "bad_request" }, 400);
    }
    if ((await answersInLastMinute(env.DB, phoneId)) >= 10) return json({ error: "slow_down" }, 429);
    const result = await recordAnswer(env.DB, { phoneId, sentenceId: b.sentenceId as number, paite, register, name });
    return result === "ok" ? json({ ok: true }) : json({ error: "closed" }, 409);
  }
```

- [ ] **Step 5: Run the answer tests**

Run: `npx vitest run test/answer.test.ts`
Expected: 7 passed.

- [ ] **Step 6: Write `test/turnstile.test.ts` (failing)**

```ts
import { env } from "cloudflare:test";
import { expect, it } from "vitest";
import { verifyTurnstile } from "../src/turnstile";

const reply = (success: boolean) => async () => new Response(JSON.stringify({ success }), { headers: { "content-type": "application/json" } });

it("passes when siteverify says success", async () => {
  expect(await verifyTurnstile("tok", "1.2.3.4", env, reply(true) as typeof fetch)).toBe(true);
});

it("fails when siteverify says no, errors, or the token is empty", async () => {
  expect(await verifyTurnstile("tok", null, env, reply(false) as typeof fetch)).toBe(false);
  expect(await verifyTurnstile("tok", null, env, (async () => { throw new Error("down"); }) as typeof fetch)).toBe(false);
  expect(await verifyTurnstile("", null, env, reply(true) as typeof fetch)).toBe(false);
});
```

- [ ] **Step 7: Write `src/turnstile.ts`**

```ts
import type { Env } from "./types";

export async function verifyTurnstile(token: string, ip: string | null, env: Env, fetcher: typeof fetch = fetch): Promise<boolean> {
  if (!token) return false;
  const form = new FormData();
  form.append("secret", env.TURNSTILE_SECRET);
  form.append("response", token);
  if (ip) form.append("remoteip", ip);
  try {
    const r = await fetcher("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: form });
    const data = await r.json<{ success?: boolean }>();
    return data.success === true;
  } catch {
    return false;
  }
}
```

- [ ] **Step 8: Add the default export to `src/index.ts`**

```ts
import { verifyTurnstile } from "./turnstile";

const app = createApp({
  verifyTurnstile: (t, ip, env) => verifyTurnstile(t, ip, env),
  verifyAccess: async () => null,
  now: () => Date.now(),
});

export default {
  fetch: (req: Request, env: Env) => app(req, env),
} satisfies ExportedHandler<Env>;
```

(`verifyAccess` becomes the real check in Task 5; until then no review route exists.)

- [ ] **Step 9: Run all tests and typecheck**

Run: `npx vitest run && npx tsc --noEmit`
Expected: all tests pass, no type errors.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "Answer submission with race-safe slot claim, rate limit, and Turnstile check"
```

---

### Task 4: Contributor page

**Files:**
- Create: `public/index.html`, `public/style.css`, `public/strings.js`, `public/app.js`

**Interfaces:**
- Consumes: `POST /api/session {phoneId, turnstileToken} → {session}`, `GET /api/next → {id, english} | 204`, `POST /api/skip {sentenceId}`, `POST /api/answer {sentenceId, paite, register, name?} → 200 | 400 | 409 | 429`. Header `X-Session`.
- Produces: the page at `/`.

- [ ] **Step 1: Copy the visual base**

Copy the `<style>` block of `daily/index.html` from `paite-open-language-data` (commit `1ec4ae3` or later) into `public/style.css`, without the `<style>` tags. Copy the `<svg class="puan" ...>...</svg>` element from the same file; it goes into `index.html` in Step 3.

- [ ] **Step 2: Write `public/strings.js`**

```js
// UI text. `pai` is filled in from the owner's Paite translations; when empty the page shows `en` only.
window.STRINGS = {
  translate: { pai: "", en: "Translate into Paite" },
  send: { pai: "", en: "Send" },
  skip: { pai: "", en: "Skip" },
  register: { pai: "", en: "Spoken / Written / Both" },
  spoken: { pai: "", en: "Spoken" },
  written: { pai: "", en: "Written" },
  both: { pai: "", en: "Both" },
  thanks: { pai: "", en: "Thank you!" },
  today: { pai: "", en: "today" },
  askName: { pai: "", en: "Want your name on the Paite contributors list?" },
  yourName: { pai: "", en: "Your name" },
  noThanks: { pai: "", en: "No thanks" },
  licence: { pai: "", en: "Your translations are given to everyone, free (public domain)" },
  loading: { pai: "", en: "Loading the next sentence…" },
  empty: { pai: "", en: "No more sentences right now. Come back tomorrow." },
  offline: { pai: "", en: "Could not send. Check your internet and try again." },
  tooFast: { pai: "", en: "Slow down a little, then try again." },
};
```

- [ ] **Step 3: Write `public/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Paite Daily</title>
<meta name="description" content="Translate simple sentences into Paite. Every answer builds open data for the Paite language.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<link rel="stylesheet" href="/style.css">
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" defer></script>
</head>
<body>
<!-- paste the <svg class="puan"> element from Step 1 here -->
<main>
  <header>
    <h1>Paite Daily</h1>
    <div class="streak" id="today"></div>
  </header>
  <section class="card" aria-live="polite">
    <div class="label" data-s="translate"></div>
    <p class="sentence" id="sentence"></p>
    <form id="form" novalidate>
      <textarea id="paite" required autocomplete="off" autocapitalize="sentences" maxlength="300" aria-label="Paite"></textarea>
      <fieldset class="register">
        <legend data-s="register"></legend>
        <label><input type="radio" name="register" value="both" checked> <span data-s="both"></span></label>
        <label><input type="radio" name="register" value="spoken"> <span data-s="spoken"></span></label>
        <label><input type="radio" name="register" value="written"> <span data-s="written"></span></label>
      </fieldset>
      <div class="actions">
        <button type="submit" class="primary" id="send" data-s="send"></button>
        <button type="button" id="skip" data-s="skip"></button>
      </div>
      <p class="licence" data-s="licence"></p>
      <p class="status" id="status" role="status"></p>
    </form>
    <div id="ask-name" hidden>
      <p data-s="askName"></p>
      <input id="name" maxlength="60" autocomplete="nickname">
      <div class="actions">
        <button type="button" class="primary" id="save-name" data-s="send"></button>
        <button type="button" id="no-name" data-s="noThanks"></button>
      </div>
    </div>
  </section>
  <div id="turnstile"></div>
</main>
<script src="/strings.js"></script>
<script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Write `public/app.js`**

```js
(() => {
  const S = window.STRINGS;
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("pd:" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem("pd:" + k, JSON.stringify(v)); } catch {} },
  };
  const t = (key) => (S[key].pai ? `${S[key].pai}` : S[key].en);
  const tBoth = (key) => (S[key].pai ? `${S[key].pai}<small>${S[key].en}</small>` : S[key].en);

  document.querySelectorAll("[data-s]").forEach((el) => { el.innerHTML = tBoth(el.dataset.s); });

  let phoneId = store.get("phone", null);
  if (!phoneId) { phoneId = crypto.randomUUID(); store.set("phone", phoneId); }
  let session = null, current = null;

  const status = (msg, ok = false) => { $("status").textContent = msg; $("status").className = "status " + (ok ? "ok" : msg ? "err" : ""); };
  const todayKey = () => "count:" + new Date().toISOString().slice(0, 10);
  const showToday = () => { const n = store.get(todayKey(), 0); $("today").textContent = n ? `🔥 ${n} ${t("today")}` : ""; };

  function turnstileToken() {
    return new Promise((resolve, reject) => {
      const go = () => window.turnstile.render("#turnstile", {
        sitekey: document.documentElement.dataset.sitekey,
        appearance: "interaction-only",
        callback: resolve,
        "error-callback": () => reject(new Error("turnstile")),
      });
      window.turnstile ? go() : window.addEventListener("load", go, { once: true });
    });
  }

  async function api(path, opts = {}) {
    if (!session) {
      const r = await fetch("/api/session", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ phoneId, turnstileToken: await turnstileToken() }) });
      if (!r.ok) throw new Error("session");
      session = (await r.json()).session;
    }
    const r = await fetch(path, { ...opts, headers: { "content-type": "application/json", "X-Session": session } });
    if (r.status === 401) { session = null; return api(path, opts); }
    return r;
  }

  async function next() {
    $("sentence").textContent = t("loading");
    $("send").disabled = true;
    try {
      const r = await api("/api/next");
      if (r.status === 204) { current = null; $("sentence").textContent = t("empty"); return; }
      current = await r.json();
      $("sentence").textContent = current.english;
      $("send").disabled = false;
      $("paite").focus();
    } catch {
      status(t("offline"));
    }
  }

  $("form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const paite = $("paite").value.trim();
    if (!current || !paite) { $("paite").focus(); return; }
    $("send").disabled = true;
    const register = new FormData($("form")).get("register");
    try {
      const r = await api("/api/answer", { method: "POST",
        body: JSON.stringify({ sentenceId: current.id, paite, register, name: store.get("name", "") }) });
      if (r.status === 429) { status(t("tooFast")); $("send").disabled = false; return; }
      if (r.ok) {
        const n = store.get(todayKey(), 0) + 1;
        store.set(todayKey(), n); showToday();
        status(n % 5 === 0 ? t("thanks") : "", true);
        if (!store.get("askedName", false)) { store.set("askedName", true); $("ask-name").hidden = false; }
      }
      $("paite").value = "";
      next();
    } catch {
      status(t("offline"));
      $("send").disabled = false;
    }
  });

  $("skip").addEventListener("click", async () => {
    if (current) { try { await api("/api/skip", { method: "POST", body: JSON.stringify({ sentenceId: current.id }) }); } catch {} }
    status("");
    next();
  });

  $("save-name").addEventListener("click", () => { store.set("name", $("name").value.trim().slice(0, 60)); $("ask-name").hidden = true; });
  $("no-name").addEventListener("click", () => { $("ask-name").hidden = true; });

  showToday();
  next();
})();
```

The Turnstile site key reaches the page as `data-sitekey` on `<html>`. Add it in `src/index.ts`: when serving `/` or `/index.html`, rewrite the asset with `HTMLRewriter`:

```ts
    if (pathname === "/" || pathname === "/index.html") {
      const page = await env.ASSETS.fetch(req);
      return new HTMLRewriter()
        .on("html", { element: (el) => el.setAttribute("data-sitekey", env.TURNSTILE_SITE_KEY) })
        .transform(page);
    }
```

Place this block in `createApp` before `return env.ASSETS.fetch(req);`, and add `"/"` and `"/index.html"` to `run_worker_first` in `wrangler.jsonc`.

- [ ] **Step 5: Add page styles for the new elements to `public/style.css`**

```css
.register { border: 0; padding: 0; margin: 0; display: flex; gap: 14px; flex-wrap: wrap; font-size: .95rem; }
.register legend { font-weight: 700; margin-bottom: 6px; }
.register label { display: inline-flex; gap: 6px; align-items: center; font-weight: 400; }
.licence { color: var(--muted); font-size: .85rem; margin: 0; }
small { display: block; font-size: .75em; color: var(--muted); font-weight: 400; }
#ask-name { display: grid; gap: 10px; border-top: 1px solid var(--line); padding-top: 14px; }
```

- [ ] **Step 6: Check the page in a browser**

Run: `npx wrangler dev` (local D1). Seed two rows:

```bash
npx wrangler d1 execute paite-daily --local --command "INSERT INTO sentences (english, english_key, source) VALUES ('Good morning.', 'good morning.', 'test'), ('I am hungry.', 'i am hungry.', 'test')"
```

Open `http://localhost:8787`. With the Turnstile test keys (site key `1x00000000000000000000AA`, secret `1x0000000000000000000000000000000AA` in `.dev.vars` as `TURNSTILE_SECRET=` and in `wrangler.jsonc` vars as `TURNSTILE_SITE_KEY` for local only), expect: a sentence card; Send records and shows the next; after the first Send the name question appears once; after both rows, the empty message shows. Check phone width (375 px): no horizontal scroll.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Contributor page: one sentence at a time, skip, optional name"
```

---

### Task 5: Access check and review API

**Files:**
- Create: `src/access.ts`, `src/reviewdb.ts`, `src/review.ts`, `test/access.test.ts`, `test/review.test.ts`
- Modify: `src/index.ts` (route `/review/api/*`, real `verifyAccess`)

**Interfaces:**
- Consumes: `json`, `Env`, `Deps`, `cleanText`.
- Produces:
  - `verifyAccess(req: Request, env: Env, getKey?: JWTVerifyGetKey): Promise<string | null>` (lower-cased email or null)
  - `reviewerName(env: Env, email: string): string | null` (null = not a reviewer)
  - `claimNext(db, email, now): Promise<ReviewCard | null>` where `ReviewCard = { sentence: { id: number; english: string }; answers: { id: number; paite: string; register: string; contributor_name: string | null; ai_note: string | null }[] }`
  - `decide(db, email, now, d: Decision): Promise<"ok" | "no_lock" | "bad_answer">` where `Decision = { sentenceId: number; decision: "accept" | "reject" | "retire"; answerId?: number; finalPaite?: string; register?: string; note?: string; alsoCorrect?: number[] }`
  - `undo(db, reviewId): Promise<"ok" | "exported" | "missing">`
  - `handleReview(req, env, deps): Promise<Response>`

- [ ] **Step 1: Write the failing access test `test/access.test.ts`**

```ts
import { env } from "cloudflare:test";
import { createLocalJWKSet, exportJWK, generateKeyPair, SignJWT } from "jose";
import { beforeAll, expect, it } from "vitest";
import { verifyAccess } from "../src/access";

let keys: Awaited<ReturnType<typeof generateKeyPair>>;
let jwks: ReturnType<typeof createLocalJWKSet>;
const cfg = { ...env, ACCESS_TEAM_DOMAIN: "lamkalabs.cloudflareaccess.com", ACCESS_AUD: "aud-123" };

beforeAll(async () => {
  keys = await generateKeyPair("RS256");
  jwks = createLocalJWKSet({ keys: [{ ...(await exportJWK(keys.publicKey)), alg: "RS256", kid: "k1" }] });
});

const token = (claims: Record<string, unknown>, aud = "aud-123", iss = "https://lamkalabs.cloudflareaccess.com") =>
  new SignJWT(claims).setProtectedHeader({ alg: "RS256", kid: "k1" }).setAudience(aud).setIssuer(iss).setExpirationTime("5m").sign(keys.privateKey);

const req = (jwt?: string) => new Request("https://paite.lamkalabs.com/review/api/next", { headers: jwt ? { "Cf-Access-Jwt-Assertion": jwt } : {} });

it("returns the email from a valid Access token", async () => {
  expect(await verifyAccess(req(await token({ email: "Rev@Example.org" })), cfg, jwks)).toBe("rev@example.org");
});

it("refuses missing, wrong-audience, and wrong-issuer tokens", async () => {
  expect(await verifyAccess(req(), cfg, jwks)).toBeNull();
  expect(await verifyAccess(req(await token({ email: "rev@example.org" }, "other-aud")), cfg, jwks)).toBeNull();
  expect(await verifyAccess(req(await token({ email: "rev@example.org" }, "aud-123", "https://evil.example")), cfg, jwks)).toBeNull();
});
```

- [ ] **Step 2: Write `src/access.ts`**

```ts
import { createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey } from "jose";
import type { Env } from "./types";

let remote: { domain: string; get: JWTVerifyGetKey } | null = null;

export async function verifyAccess(req: Request, env: Env, getKey?: JWTVerifyGetKey): Promise<string | null> {
  const jwt = req.headers.get("Cf-Access-Jwt-Assertion");
  if (!jwt || !env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD) return null;
  if (!getKey) {
    if (remote?.domain !== env.ACCESS_TEAM_DOMAIN) {
      remote = { domain: env.ACCESS_TEAM_DOMAIN, get: createRemoteJWKSet(new URL(`https://${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`)) };
    }
    getKey = remote.get;
  }
  try {
    const { payload } = await jwtVerify(jwt, getKey, { issuer: `https://${env.ACCESS_TEAM_DOMAIN}`, audience: env.ACCESS_AUD });
    return typeof payload.email === "string" ? payload.email.toLowerCase() : null;
  } catch {
    return null;
  }
}

export function reviewerName(env: Env, email: string): string | null {
  try {
    const map = JSON.parse(env.REVIEWERS) as Record<string, string>;
    for (const [k, v] of Object.entries(map)) if (k.toLowerCase() === email) return v;
  } catch {}
  return null;
}
```

- [ ] **Step 3: Run the access test**

Run: `npx vitest run test/access.test.ts`
Expected: 2 passed.

- [ ] **Step 4: Write the failing review tests `test/review.test.ts`**

```ts
import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { addSentences, call, fakeDeps, NOW, PHONE_A, PHONE_B, session } from "./helpers";

const as = (email: string | null, now = NOW) => fakeDeps({ verifyAccess: async () => email, now: () => now });
const rev = (path: string, body?: unknown, email: string | null = "rev@example.org", now = NOW) =>
  call(path, body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }, as(email, now));

async function fullSentence(english = "I am well.", answers = ["Ka dam e.", "Ka dam."]) {
  const [id] = await addSentences(english);
  const phones = [PHONE_A, PHONE_B];
  for (let i = 0; i < answers.length; i++) {
    await call("/api/answer", { method: "POST", session: await session(phones[i]), body: JSON.stringify({ sentenceId: id, paite: answers[i], register: "both" }) });
  }
  return id;
}

describe("review access", () => {
  it("refuses requests without a valid Access identity", async () => {
    expect((await rev("/review/api/next", undefined, null)).status).toBe(401);
  });
  it("refuses a signed-in person who is not on the reviewer list", async () => {
    expect((await rev("/review/api/next", undefined, "stranger@example.org")).status).toBe(403);
  });
});

describe("review flow", () => {
  it("serves a full sentence with its answers and locks it", async () => {
    const id = await fullSentence();
    const card = await (await rev("/review/api/next")).json<{ sentence: { id: number }; answers: { paite: string }[] }>();
    expect(card.sentence.id).toBe(id);
    expect(card.answers.map((a) => a.paite).sort()).toEqual(["Ka dam e.", "Ka dam."]);
    expect((await rev("/review/api/next", undefined, "owner@example.org")).status).toBe(204);
  });

  it("accept verifies the sentence and records the reviewer", async () => {
    const id = await fullSentence();
    const card = await (await rev("/review/api/next")).json<{ answers: { id: number; paite: string }[] }>();
    const chosen = card.answers.find((a) => a.paite === "Ka dam e.")!;
    const other = card.answers.find((a) => a.paite !== "Ka dam e.")!;
    const r = await rev("/review/api/decide", { sentenceId: id, decision: "accept", answerId: chosen.id, register: "spoken", alsoCorrect: [other.id] });
    expect(r.status).toBe(200);
    expect(await env.DB.prepare("SELECT status FROM sentences WHERE id = ?1").bind(id).first()).toEqual({ status: "verified" });
    const review = await env.DB.prepare("SELECT reviewer_email, final_paite, register FROM reviews WHERE sentence_id = ?1").bind(id).first();
    expect(review).toEqual({ reviewer_email: "rev@example.org", final_paite: "Ka dam e.", register: "spoken" });
    const statuses = await env.DB.prepare("SELECT status FROM answers WHERE sentence_id = ?1 ORDER BY status").bind(id).all();
    expect(statuses.results.map((s) => s.status)).toEqual(["accepted", "also_correct"]);
  });

  it("fix: accept with edited text stores the edited text", async () => {
    const id = await fullSentence();
    const card = await (await rev("/review/api/next")).json<{ answers: { id: number }[] }>();
    await rev("/review/api/decide", { sentenceId: id, decision: "accept", answerId: card.answers[0].id, finalPaite: "  Ka dam  e. " });
    const review = await env.DB.prepare("SELECT final_paite FROM reviews WHERE sentence_id = ?1").bind(id).first();
    expect(review).toEqual({ final_paite: "Ka dam e." });
  });

  it("reject reopens the sentence for new answers", async () => {
    const id = await fullSentence();
    await rev("/review/api/next");
    await rev("/review/api/decide", { sentenceId: id, decision: "reject" });
    expect(await env.DB.prepare("SELECT status, answer_count FROM sentences WHERE id = ?1").bind(id).first()).toEqual({ status: "open", answer_count: 0 });
  });

  it("deciding without holding the lock is refused", async () => {
    const id = await fullSentence();
    expect((await rev("/review/api/decide", { sentenceId: id, decision: "reject" })).status).toBe(409);
  });

  it("expired lock is refused", async () => {
    const id = await fullSentence();
    await rev("/review/api/next", undefined, "rev@example.org", NOW);
    const later = NOW + 11 * 60_000;
    await rev("/review/api/next", undefined, "owner@example.org", later);
    expect((await rev("/review/api/decide", { sentenceId: id, decision: "reject" }, "rev@example.org", later)).status).toBe(409);
  });

  it("owner can undo a decision that is not yet exported; others cannot", async () => {
    const id = await fullSentence();
    const card = await (await rev("/review/api/next")).json<{ answers: { id: number }[] }>();
    await rev("/review/api/decide", { sentenceId: id, decision: "accept", answerId: card.answers[0].id });
    const { id: reviewId } = (await env.DB.prepare("SELECT id FROM reviews WHERE sentence_id = ?1").bind(id).first<{ id: number }>())!;
    expect((await rev("/review/api/undo", { reviewId })).status).toBe(403);
    expect((await rev("/review/api/undo", { reviewId }, "owner@example.org")).status).toBe(200);
    expect(await env.DB.prepare("SELECT status FROM sentences WHERE id = ?1").bind(id).first()).toEqual({ status: "full" });
  });
});
```

- [ ] **Step 5: Run to verify failure**

Run: `npx vitest run test/review.test.ts`
Expected: FAIL, review routes return 404 or assets.

- [ ] **Step 6: Write `src/reviewdb.ts`**

```ts
import { cleanText } from "./text";

const LOCK_MS = 10 * 60_000;

export type ReviewCard = {
  sentence: { id: number; english: string };
  answers: { id: number; paite: string; register: string; contributor_name: string | null; ai_note: string | null }[];
};

export type Decision = {
  sentenceId: number;
  decision: "accept" | "reject" | "retire";
  answerId?: number;
  finalPaite?: string;
  register?: string;
  note?: string;
  alsoCorrect?: number[];
};

export async function claimNext(db: D1Database, email: string, now: number): Promise<ReviewCard | null> {
  const candidates = await db
    .prepare(
      `SELECT s.id, s.english FROM sentences s
       WHERE s.status IN ('open', 'full')
         AND EXISTS (SELECT 1 FROM answers a WHERE a.sentence_id = s.id AND a.status = 'new')
         AND NOT EXISTS (SELECT 1 FROM locks l WHERE l.sentence_id = s.id AND l.expires_at > ?1 AND l.reviewer_email <> ?2)
       ORDER BY (s.status = 'full') DESC, s.id
       LIMIT 5`,
    )
    .bind(now, email)
    .all<{ id: number; english: string }>();
  for (const s of candidates.results) {
    const lock = await db
      .prepare(
        `INSERT INTO locks (sentence_id, reviewer_email, expires_at) VALUES (?1, ?2, ?3)
         ON CONFLICT (sentence_id) DO UPDATE SET reviewer_email = excluded.reviewer_email, expires_at = excluded.expires_at
         WHERE locks.expires_at <= ?4 OR locks.reviewer_email = excluded.reviewer_email`,
      )
      .bind(s.id, email, now + LOCK_MS, now)
      .run();
    if (lock.meta.changes !== 1) continue;
    const answers = await db
      .prepare("SELECT id, paite, register, contributor_name, ai_note FROM answers WHERE sentence_id = ?1 AND status = 'new' ORDER BY id")
      .bind(s.id)
      .all<ReviewCard["answers"][number]>();
    return { sentence: s, answers: answers.results };
  }
  return null;
}

async function holdsLock(db: D1Database, sentenceId: number, email: string, now: number): Promise<boolean> {
  const l = await db.prepare("SELECT 1 AS ok FROM locks WHERE sentence_id = ?1 AND reviewer_email = ?2 AND expires_at > ?3")
    .bind(sentenceId, email, now).first();
  return !!l;
}

export async function decide(db: D1Database, email: string, now: number, d: Decision): Promise<"ok" | "no_lock" | "bad_answer"> {
  if (!(await holdsLock(db, d.sentenceId, email, now))) return "no_lock";
  const note = d.note ? cleanText(d.note, 300) : null;
  const register = ["spoken", "written", "both"].includes(d.register ?? "") ? d.register! : null;
  const stmts: D1PreparedStatement[] = [];

  if (d.decision === "accept") {
    const chosen = await db.prepare("SELECT paite, register FROM answers WHERE id = ?1 AND sentence_id = ?2 AND status = 'new'")
      .bind(d.answerId ?? -1, d.sentenceId).first<{ paite: string; register: string }>();
    if (!chosen) return "bad_answer";
    const finalPaite = d.finalPaite !== undefined ? cleanText(d.finalPaite, 300) : chosen.paite;
    if (!finalPaite) return "bad_answer";
    const also = (d.alsoCorrect ?? []).filter((x) => Number.isInteger(x) && x !== d.answerId);
    stmts.push(
      db.prepare("UPDATE answers SET status = 'accepted' WHERE id = ?1").bind(d.answerId),
      ...also.map((id) => db.prepare("UPDATE answers SET status = 'also_correct' WHERE id = ?1 AND sentence_id = ?2 AND status = 'new'").bind(id, d.sentenceId)),
      db.prepare("UPDATE answers SET status = 'rejected' WHERE sentence_id = ?1 AND status = 'new'").bind(d.sentenceId),
      db.prepare("UPDATE sentences SET status = 'verified' WHERE id = ?1").bind(d.sentenceId),
      db.prepare("INSERT INTO reviews (sentence_id, reviewer_email, decision, accepted_answer_id, final_paite, register, note) VALUES (?1, ?2, 'accept', ?3, ?4, ?5, ?6)")
        .bind(d.sentenceId, email, d.answerId, finalPaite, register ?? chosen.register, note),
    );
  } else {
    stmts.push(
      db.prepare("UPDATE answers SET status = 'rejected' WHERE sentence_id = ?1 AND status = 'new'").bind(d.sentenceId),
      d.decision === "reject"
        ? db.prepare("UPDATE sentences SET status = 'open', answer_count = 0 WHERE id = ?1").bind(d.sentenceId)
        : db.prepare("UPDATE sentences SET status = 'retired' WHERE id = ?1").bind(d.sentenceId),
      db.prepare("INSERT INTO reviews (sentence_id, reviewer_email, decision, note) VALUES (?1, ?2, ?3, ?4)").bind(d.sentenceId, email, d.decision, note),
    );
  }
  stmts.push(db.prepare("DELETE FROM locks WHERE sentence_id = ?1").bind(d.sentenceId));
  await db.batch(stmts);
  return "ok";
}

export async function undo(db: D1Database, reviewId: number): Promise<"ok" | "exported" | "missing"> {
  const r = await db.prepare("SELECT sentence_id, decision FROM reviews WHERE id = ?1 AND undone_at IS NULL").bind(reviewId)
    .first<{ sentence_id: number; decision: string }>();
  if (!r) return "missing";
  const last = await db.prepare("SELECT COALESCE(MAX(last_review_id), 0) AS n FROM exports").first<{ n: number }>();
  if (reviewId <= (last?.n ?? 0)) return "exported";
  const { n } = (await db.prepare("SELECT count(*) AS n FROM answers WHERE sentence_id = ?1").bind(r.sentence_id).first<{ n: number }>())!;
  await db.batch([
    db.prepare("UPDATE reviews SET undone_at = datetime('now') WHERE id = ?1").bind(reviewId),
    db.prepare("UPDATE answers SET status = 'new' WHERE sentence_id = ?1").bind(r.sentence_id),
    db.prepare("UPDATE sentences SET status = CASE WHEN ?2 >= 2 THEN 'full' ELSE 'open' END, answer_count = ?2 WHERE id = ?1").bind(r.sentence_id, Math.min(n, 2)),
  ]);
  return "ok";
}
```

Note on reject: answers rejected earlier keep `status = 'rejected'`; `undo` of a reject restores them to `new`. The `answer_count` restored is the number of answer rows, capped at 2.

- [ ] **Step 7: Write `src/review.ts`**

```ts
import { reviewerName } from "./access";
import { claimNext, decide, undo, type Decision } from "./reviewdb";
import { json, type Deps, type Env } from "./types";

export async function handleReview(req: Request, env: Env, deps: Deps): Promise<Response> {
  const email = await deps.verifyAccess(req, env);
  if (!email) return json({ error: "sign_in" }, 401);
  if (!reviewerName(env, email)) return json({ error: "not_a_reviewer" }, 403);
  const { pathname } = new URL(req.url);
  let b: Record<string, unknown> = {};
  if (req.method === "POST") { try { b = (await req.json()) as Record<string, unknown>; } catch {} }

  if (pathname === "/review/api/next" && req.method === "GET") {
    const card = await claimNext(env.DB, email, deps.now());
    return card ? json(card) : new Response(null, { status: 204 });
  }
  if (pathname === "/review/api/decide" && req.method === "POST") {
    if (!Number.isInteger(b.sentenceId) || !["accept", "reject", "retire"].includes(b.decision as string)) return json({ error: "bad_request" }, 400);
    const result = await decide(env.DB, email, deps.now(), b as unknown as Decision);
    if (result === "no_lock") return json({ error: "lock_lost" }, 409);
    if (result === "bad_answer") return json({ error: "bad_answer" }, 400);
    return json({ ok: true });
  }
  if (pathname === "/review/api/undo" && req.method === "POST") {
    if (email !== env.OWNER_EMAIL.toLowerCase()) return json({ error: "owner_only" }, 403);
    const result = await undo(env.DB, b.reviewId as number);
    return result === "ok" ? json({ ok: true }) : json({ error: result }, result === "missing" ? 404 : 409);
  }
  if (pathname === "/review/api/me" && req.method === "GET") {
    return json({ name: reviewerName(env, email), owner: email === env.OWNER_EMAIL.toLowerCase() });
  }
  return json({ error: "not_found" }, 404);
}
```

- [ ] **Step 8: Route it in `src/index.ts`**

In `createApp`, before the asset fallthrough:

```ts
    if (pathname.startsWith("/review/api/")) return handleReview(req, env, deps);
```

Import `handleReview` from `./review` and `verifyAccess` from `./access`, and in the default `app` replace `verifyAccess: async () => null` with `verifyAccess: (req, env) => verifyAccess(req, env)`.

- [ ] **Step 9: Run all tests and typecheck**

Run: `npx vitest run && npx tsc --noEmit`
Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "Review API behind Cloudflare Access: locks, accept/fix/reject/retire, owner undo"
```

---

### Task 6: Reviewer page

**Files:**
- Create: `public/review/index.html`, `public/review/review.js`

**Interfaces:**
- Consumes: `GET /review/api/me`, `GET /review/api/next`, `POST /review/api/decide`, `POST /review/api/undo` (Task 5).

- [ ] **Step 1: Write `public/review/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Paite Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<link rel="stylesheet" href="/style.css">
<style>
  .answer { display: grid; gap: 8px; border: 1px solid var(--line); border-radius: 10px; padding: 12px; }
  .answer p { margin: 0; font-size: 1.2rem; }
  .meta { color: var(--muted); font-size: .85rem; }
  .ai { background: var(--bg); border-radius: 8px; padding: 8px 10px; font-size: .9rem; }
  .row3 { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
</head>
<body>
<main>
  <header><h1>Paite Review</h1><div class="streak" id="who"></div></header>
  <section class="card" id="card">
    <div class="label">English</div>
    <p class="sentence" id="english">Loading…</p>
    <div id="answers" style="display:grid;gap:10px"></div>
    <label>Register of the accepted answer
      <select id="register"><option value="">As given</option><option value="spoken">Spoken</option><option value="written">Written</option><option value="both">Both</option></select>
    </label>
    <label>Note (optional)<input id="note" maxlength="300"></label>
    <div class="row3">
      <button type="button" id="reject">❌ Reject all</button>
      <button type="button" id="retire">Retire sentence</button>
    </div>
    <p class="status" id="status" role="status"></p>
  </section>
</main>
<script src="/review/review.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `public/review/review.js`**

```js
(() => {
  const $ = (id) => document.getElementById(id);
  let card = null;

  const status = (m, ok = false) => { $("status").textContent = m; $("status").className = "status " + (ok ? "ok" : m ? "err" : ""); };
  const post = (path, body) => fetch(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

  async function me() {
    const r = await fetch("/review/api/me");
    if (r.status === 403) { $("english").textContent = "You are not a reviewer. Ask the owner to add your email."; return false; }
    if (!r.ok) { $("english").textContent = "Sign-in needed. Reload the page."; return false; }
    const m = await r.json();
    $("who").textContent = m.name;
    return true;
  }

  function render() {
    $("english").textContent = card.sentence.english;
    $("answers").replaceChildren(...card.answers.map((a) => {
      const box = document.createElement("div");
      box.className = "answer";
      const p = document.createElement("p"); p.textContent = a.paite;
      const meta = document.createElement("div"); meta.className = "meta";
      meta.textContent = `${a.register}${a.contributor_name ? " · " + a.contributor_name : ""}`;
      box.append(p, meta);
      if (a.ai_note) { const ai = document.createElement("div"); ai.className = "ai"; ai.textContent = "AI note: " + a.ai_note; box.append(ai); }
      const edit = document.createElement("textarea"); edit.value = a.paite; edit.maxLength = 300; edit.setAttribute("aria-label", "Edit before accepting");
      const also = document.createElement("label"); also.innerHTML = '<input type="checkbox"> Also correct';
      also.querySelector("input").dataset.answerId = a.id;
      const accept = document.createElement("button"); accept.className = "primary"; accept.textContent = "✅ Accept this";
      accept.addEventListener("click", () => send({
        decision: "accept", answerId: a.id,
        finalPaite: edit.value.trim() === a.paite ? undefined : edit.value,
        alsoCorrect: [...document.querySelectorAll("[data-answer-id]:checked")].map((c) => Number(c.dataset.answerId)),
      }));
      box.append(edit, also, accept);
      return box;
    }));
  }

  async function next() {
    status("");
    $("english").textContent = "Loading…";
    const r = await fetch("/review/api/next");
    if (r.status === 204) { card = null; $("english").textContent = "Nothing to review right now. 🎉"; $("answers").replaceChildren(); return; }
    card = await r.json();
    $("note").value = ""; $("register").value = "";
    render();
  }

  async function send(extra) {
    if (!card) return;
    const r = await post("/review/api/decide", {
      sentenceId: card.sentence.id, register: $("register").value || undefined, note: $("note").value || undefined, ...extra,
    });
    if (r.status === 409) { status("Someone else took this one. Loading the next."); }
    else if (!r.ok) { status("Could not save. Try again."); return; }
    else status("Saved.", true);
    next();
  }

  $("reject").addEventListener("click", () => send({ decision: "reject" }));
  $("retire").addEventListener("click", () => send({ decision: "retire" }));

  me().then((ok) => ok && next());
})();
```

- [ ] **Step 3: Check the page locally**

`wrangler dev` has no Access. For a local check only, run tests instead of the page for auth, and check the layout by opening `http://localhost:8787/review/` (the API calls return 401, and the page shows "Sign-in needed"). The full flow is checked on the deployed app in Task 8, Step 9.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Reviewer page: one sentence at a time with accept, fix, reject, retire"
```

---

### Task 7: Nightly export and owner-translation retirement

**Files:**
- Create: `src/export.ts`, `test/export.test.ts`
- Modify: `src/index.ts` (add `scheduled`)

**Interfaces:**
- Consumes: D1 tables; `normaliseEnglish`; `reviewerName`.
- Produces:
  - `exportVerified(env: Env, fetcher: typeof fetch): Promise<{ exported: number; path: string | null }>`
  - `retireOwnerTranslations(env: Env, fetcher: typeof fetch): Promise<number>`
  - `runNightly(env: Env, fetcher: typeof fetch): Promise<void>` (logs each job in `job_runs`)
  - `toBase64Utf8(s: string): string`

- [ ] **Step 1: Write the failing tests `test/export.test.ts`**

```ts
import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { exportVerified, retireOwnerTranslations, runNightly, toBase64Utf8 } from "../src/export";
import { addSentences } from "./helpers";

type Put = { url: string; body: { message: string; content: string; branch: string } };

function github(existing: Set<string> = new Set()) {
  const puts: Put[] = [];
  const fetcher = (async (input: RequestInfo, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.url;
    if (init?.method === "PUT") {
      const path = url.split("/contents/")[1];
      if (existing.has(path)) return new Response("{}", { status: 422 });
      puts.push({ url, body: JSON.parse(init.body as string) });
      return new Response("{}", { status: 201 });
    }
    return new Response("not found", { status: 404 });
  }) as typeof fetch;
  return { puts, fetcher };
}

async function verified(english: string, paite: string, name: string | null = "Mang") {
  const [id] = await addSentences(english);
  const a = await env.DB.prepare("INSERT INTO answers (sentence_id, paite, register, phone_id, contributor_name, status) VALUES (?1, ?2, 'both', 'p', ?3, 'accepted') RETURNING id")
    .bind(id, paite, name).first<{ id: number }>();
  await env.DB.prepare("UPDATE sentences SET status = 'verified' WHERE id = ?1").bind(id).run();
  await env.DB.prepare("INSERT INTO reviews (sentence_id, reviewer_email, decision, accepted_answer_id, final_paite, register) VALUES (?1, 'rev@example.org', 'accept', ?2, ?3, 'spoken')")
    .bind(id, a!.id, paite).run();
  return id;
}

const decode = (b64: string) => new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));

describe("export", () => {
  it("encodes UTF-8 to base64", () => {
    expect(decode(toBase64Utf8("Pathian — ā"))).toBe("Pathian — ā");
  });

  it("writes one JSON line per accepted review, with reviewer display name and CC0", async () => {
    await verified("I am well.", "Ka dam e.");
    await verified("Good night for now.", "Mangpha phot le.", null);
    const gh = github();
    const r = await exportVerified(env, gh.fetcher);
    expect(r.exported).toBe(2);
    expect(gh.puts).toHaveLength(1);
    expect(gh.puts[0].url).toMatch(/\/repos\/khooptong-sudo\/paite-open-language-data\/contents\/community\/verified-\d+-\d+\.jsonl$/);
    const lines = decode(gh.puts[0].body.content).trim().split("\n").map((l) => JSON.parse(l));
    expect(lines[0]).toMatchObject({ english: "I am well.", paite: "Ka dam e.", register: "spoken", contributor: "Mang", verified_by: "Rev One", licence: "CC0-1.0" });
    expect(lines[1].contributor).toBe("");
    expect(JSON.stringify(lines)).not.toContain("rev@example.org");
  });

  it("does nothing when there is nothing new", async () => {
    const gh = github();
    expect((await exportVerified(env, gh.fetcher)).exported).toBe(0);
    expect(gh.puts).toHaveLength(0);
  });

  it("rerun after partial export does not duplicate", async () => {
    await verified("I am well.", "Ka dam e.");
    const first = github();
    await exportVerified(env, first.fetcher);
    const path = first.puts[0].url.split("/contents/")[1];
    await env.DB.prepare("DELETE FROM exports").run(); // simulate: GitHub saved, D1 did not
    const second = github(new Set([path]));
    const r = await exportVerified(env, second.fetcher);
    expect(second.puts).toHaveLength(0);
    expect(r.exported).toBe(1);
    const n = await env.DB.prepare("SELECT count(*) AS n FROM exports").first<{ n: number }>();
    expect(n!.n).toBe(1);
  });

  it("skips undone reviews", async () => {
    const id = await verified("I am well.", "Ka dam e.");
    await env.DB.prepare("UPDATE reviews SET undone_at = datetime('now') WHERE sentence_id = ?1").bind(id).run();
    const gh = github();
    expect((await exportVerified(env, gh.fetcher)).exported).toBe(0);
  });
});

describe("owner translations", () => {
  it("retires open, unanswered sentences the owner already translated", async () => {
    const [done, answered, other] = await addSentences("I am hungry.", "Good morning.", "Have you eaten?");
    await env.DB.prepare("UPDATE sentences SET answer_count = 1 WHERE id = ?1").bind(answered).run();
    const corrections = { corrections: [
      { english: "I am hungry.", status: "verified" },
      { english: "Good morning.", status: "verified" },
      { english: "Have you eaten?", status: "pending" },
    ] };
    const fetcher = (async () => new Response(JSON.stringify(corrections))) as typeof fetch;
    expect(await retireOwnerTranslations(env, fetcher)).toBe(1);
    const rows = await env.DB.prepare("SELECT id, status FROM sentences ORDER BY id").all<{ id: number; status: string }>();
    expect(rows.results).toEqual([{ id: done, status: "retired" }, { id: answered, status: "open" }, { id: other, status: "open" }]);
  });
});

it("runNightly logs both jobs, even when one fails", async () => {
  const failing = (async () => { throw new Error("network down"); }) as typeof fetch;
  await runNightly(env, failing);
  const runs = await env.DB.prepare("SELECT job, ok FROM job_runs ORDER BY id").all();
  expect(runs.results).toEqual([{ job: "export", ok: 1 }, { job: "retire_owner", ok: 0 }]);
});
```

(In the last test the export finds nothing new, so it succeeds without a network call; the retirement job fails on the network and is logged.)

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/export.test.ts`
Expected: FAIL, cannot import `../src/export`.

- [ ] **Step 3: Write `src/export.ts`**

```ts
import { reviewerName } from "./access";
import { normaliseEnglish } from "./text";
import type { Env } from "./types";

export function toBase64Utf8(s: string): string {
  const bytes = new TextEncoder().encode(s);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

type Row = {
  review_id: number; sentence_id: number; english: string; final_paite: string; register: string;
  reviewer_email: string; created_at: string; contributor_name: string | null;
};

export async function exportVerified(env: Env, fetcher: typeof fetch): Promise<{ exported: number; path: string | null }> {
  const last = (await env.DB.prepare("SELECT COALESCE(MAX(last_review_id), 0) AS n FROM exports").first<{ n: number }>())!.n;
  const { results } = await env.DB.prepare(
    `SELECT r.id AS review_id, s.id AS sentence_id, s.english, r.final_paite, r.register, r.reviewer_email, r.created_at,
            a.contributor_name
     FROM reviews r
     JOIN sentences s ON s.id = r.sentence_id
     LEFT JOIN answers a ON a.id = r.accepted_answer_id
     WHERE r.id > ?1 AND r.decision = 'accept' AND r.undone_at IS NULL
     ORDER BY r.id`,
  ).bind(last).all<Row>();
  if (results.length === 0) return { exported: 0, path: null };

  const lines: string[] = [];
  for (const row of results) {
    const also = await env.DB.prepare("SELECT paite FROM answers WHERE sentence_id = ?1 AND status = 'also_correct' ORDER BY id")
      .bind(row.sentence_id).all<{ paite: string }>();
    lines.push(JSON.stringify({
      id: `community:${row.sentence_id}`,
      english: row.english,
      paite: row.final_paite,
      register: row.register,
      contributor: row.contributor_name ?? "",
      verified_by: reviewerName(env, row.reviewer_email.toLowerCase()) ?? "Reviewer",
      verified_at: row.created_at,
      licence: "CC0-1.0",
      also_correct: also.results.map((x) => x.paite),
    }));
  }

  const first = results[0].review_id;
  const lastId = results[results.length - 1].review_id;
  const path = `community/verified-${first}-${lastId}.jsonl`;
  const res = await fetcher(`https://api.github.com/repos/${env.CORPUS_REPO}/contents/${path}`, {
    method: "PUT",
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "user-agent": "paite-daily",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      message: `community: ${results.length} verified sentences (reviews ${first}-${lastId})`,
      content: toBase64Utf8(lines.join("\n") + "\n"),
      branch: env.CORPUS_BRANCH,
    }),
  });
  // 422 = the file already exists: an earlier run saved it but did not record it. Record it now.
  if (!res.ok && res.status !== 422) throw new Error(`GitHub PUT ${res.status}`);
  await env.DB.prepare("INSERT INTO exports (first_review_id, last_review_id, path) VALUES (?1, ?2, ?3)").bind(first, lastId, path).run();
  return { exported: results.length, path };
}

export async function retireOwnerTranslations(env: Env, fetcher: typeof fetch): Promise<number> {
  const url = `https://raw.githubusercontent.com/${env.CORPUS_REPO}/${env.CORPUS_BRANCH}/corrections.json`;
  const res = await fetcher(url);
  if (!res.ok) throw new Error(`corrections.json ${res.status}`);
  const data = (await res.json()) as { corrections: { english: string; status: string }[] };
  const keys = [...new Set(data.corrections.filter((c) => c.status === "verified").map((c) => normaliseEnglish(c.english)))];
  let retired = 0;
  for (let i = 0; i < keys.length; i += 50) {
    const chunk = keys.slice(i, i + 50);
    const r = await env.DB.prepare(
      `UPDATE sentences SET status = 'retired'
       WHERE status = 'open' AND answer_count = 0 AND english_key IN (${chunk.map((_, j) => `?${j + 1}`).join(",")})`,
    ).bind(...chunk).run();
    retired += r.meta.changes;
  }
  return retired;
}

async function logged(env: Env, job: string, fn: () => Promise<unknown>): Promise<void> {
  try {
    const result = await fn();
    await env.DB.prepare("INSERT INTO job_runs (job, ok, detail) VALUES (?1, 1, ?2)").bind(job, JSON.stringify(result)).run();
  } catch (e) {
    console.error(job, e);
    await env.DB.prepare("INSERT INTO job_runs (job, ok, detail) VALUES (?1, 0, ?2)").bind(job, String(e)).run();
  }
}

export async function runNightly(env: Env, fetcher: typeof fetch): Promise<void> {
  await logged(env, "export", () => exportVerified(env, fetcher));
  await logged(env, "retire_owner", () => retireOwnerTranslations(env, fetcher));
}
```

- [ ] **Step 4: Add `scheduled` to the default export in `src/index.ts`**

```ts
import { runNightly } from "./export";

export default {
  fetch: (req: Request, env: Env) => app(req, env),
  scheduled: async (_c: ScheduledController, env: Env, ctx: ExecutionContext) => {
    ctx.waitUntil(runNightly(env, fetch));
  },
} satisfies ExportedHandler<Env>;
```

- [ ] **Step 5: Run all tests and typecheck**

Run: `npx vitest run && npx tsc --noEmit`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Nightly export to the dataset repo and retirement of owner-translated sentences"
```

---

### Task 8: Seed, dataset-side changes, deploy, launch check

**Files (paite-daily):**
- Create: `scripts/seed.mjs`, `README.md`
- Modify: `wrangler.jsonc` (real `database_id`, route, vars)

**Files (paite-open-language-data):**
- Modify: `scripts/build_training.py`, `LICENSE`, `README.md`, `daily/index.html`
- Create: `community/.gitkeep`

**Interfaces:**
- Consumes: everything above; `prompts/everyday_en.txt` in the dataset repo.

- [ ] **Step 1: Write `scripts/seed.mjs`**

```js
// Usage: node scripts/seed.mjs ../paite_corpus/prompts/everyday_en.txt > seed.sql
import { readFileSync } from "node:fs";

const norm = (s) => s.normalize("NFC").trim().replace(/\s+/g, " ").toLowerCase(); // same rule as src/text.ts normaliseEnglish
const q = (s) => `'${s.replace(/'/g, "''")}'`;
const lines = readFileSync(process.argv[2], "utf8").split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
for (const l of lines) console.log(`INSERT OR IGNORE INTO sentences (english, english_key, source) VALUES (${q(l)}, ${q(norm(l))}, 'prompts');`);
```

Run: `node scripts/seed.mjs F:/Resources/paite_corpus/prompts/everyday_en.txt > seed.sql`
Expected: 196 `INSERT` lines; `grep -c INSERT seed.sql` prints `196`.

- [ ] **Step 2: Read community files in `scripts/build_training.py` (dataset repo)**

Add after the `verified_words` loop:

```python
    for path in sorted((ROOT / "community").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for k, paite in enumerate([row["paite"], *row.get("also_correct", [])]):
                row_id = row["id"] if k == 0 else f"{row['id']}:{k}"
                parallel.append({"id": row_id, "paite": paite, "english": row["english"],
                                 "source": "community", "split": split_for_sentence(paite, row["id"])})
```

(`split_for_sentence` uses `row["id"]` for every variant, so all variants of one sentence share one split.)

Create `community/.gitkeep` (empty). Run `python scripts/build_training.py`; expected: same row counts as before (no community files yet), exit 0.

- [ ] **Step 3: Add the CC0 section to `LICENSE` and redirect the old page (dataset repo)**

In `LICENSE`, add after section 2:

```
2a. Public domain dedication (CC0 1.0)

   - Every file in community/. These are translations sent through
     Paite Daily (paite.lamkalabs.com) and verified by reviewers. The
     contributors dedicated them to the public domain:
     https://creativecommons.org/publicdomain/zero/1.0/
```

Replace the whole body of `daily/index.html` with:

```html
<!doctype html>
<meta charset="utf-8">
<title>Paite Daily</title>
<meta http-equiv="refresh" content="0; url=https://paite.lamkalabs.com/">
<link rel="canonical" href="https://paite.lamkalabs.com/">
<p>Paite Daily has moved to <a href="https://paite.lamkalabs.com/">paite.lamkalabs.com</a>.</p>
```

In `README.md`, replace every `https://khooptong-sudo.github.io/paite-open-language-data/daily/` with `https://paite.lamkalabs.com/`, and add a `community/` row to the Contents table: `` | `community/` | Translations from Paite Daily, verified by reviewers (CC0) | Grows nightly | ``.

Commit and push the dataset repo:

```bash
git add -A
git commit -m "Accept community translations from Paite Daily (CC0); redirect old page"
git push
```

Wait for the "Check data" workflow: `gh run watch <id> --exit-status`; expected: success.

- [ ] **Step 4: Owner steps (the owner runs these; they need the owner's accounts)**

1. `npx wrangler login` in `F:\Resources\paite-daily`.
2. Cloudflare dashboard → Zero Trust → create a team (free plan). Note the team domain, for example `lamkalabs.cloudflareaccess.com`.
3. Zero Trust → Access → Applications → Add self-hosted application: domain `paite.lamkalabs.com`, path `review`. Policy: Allow, Include → Emails → the reviewer emails. Login method: One-time PIN. Note the Application Audience (AUD) tag.
4. Turnstile → Add widget for `paite.lamkalabs.com`, mode Invisible. Note the site key and secret.
5. GitHub → Settings → Developer settings → Fine-grained tokens → new token: only repository `paite-open-language-data`, permission Contents: Read and write.

- [ ] **Step 5: Create the database and fill in configuration**

```bash
npx wrangler d1 create paite-daily
```

Copy the printed `database_id` into `wrangler.jsonc`. Set the vars in `wrangler.jsonc`: `ACCESS_TEAM_DOMAIN` (Step 4.2), `ACCESS_AUD` (Step 4.3), `TURNSTILE_SITE_KEY` (Step 4.4), `OWNER_EMAIL`, `REVIEWERS` (JSON map of each reviewer email to display name). Add the domain:

```jsonc
  "routes": [{ "pattern": "paite.lamkalabs.com", "custom_domain": true }],
```

Then the owner sets the secrets (each command prompts for the value):

```bash
npx wrangler secret put TURNSTILE_SECRET
npx wrangler secret put SESSION_SECRET
npx wrangler secret put GITHUB_TOKEN
```

For `SESSION_SECRET`, paste the output of `node -e "console.log(crypto.randomUUID()+crypto.randomUUID())"`.

- [ ] **Step 6: Migrate, seed, deploy**

```bash
npx wrangler d1 migrations apply paite-daily --remote
npx wrangler d1 execute paite-daily --remote --file seed.sql
npx wrangler d1 execute paite-daily --remote --command "SELECT count(*) AS n FROM sentences"
npm run deploy
```

Expected: count `196`; deploy prints `paite.lamkalabs.com` as a custom domain.

- [ ] **Step 7: Retire the owner's existing translations once**

```bash
npx wrangler d1 execute paite-daily --remote --command "SELECT count(*) FROM sentences WHERE status='open'"
```

Trigger the cron once from the dashboard (Workers → paite-daily → Settings → Triggers → Cron → Test), or wait for 03:00 UTC. Then check `job_runs`:

```bash
npx wrangler d1 execute paite-daily --remote --command "SELECT job, ok, detail FROM job_runs ORDER BY id DESC LIMIT 2"
```

Expected: `export` ok (0 exported), `retire_owner` ok.

- [ ] **Step 8: Write `README.md` for the app repo, create the GitHub repo, push**

`README.md` content: one paragraph on what the app does, the live link, the owner steps of Step 4, the commands of Steps 5-6, and "Run tests: `npm test`". Then:

```bash
gh repo create khooptong-sudo/paite-daily --public --source . --push --description "Paite Daily: community translation collection for the Paite language"
```

- [ ] **Step 9: Launch check (owner and one reviewer)**

1. On a phone, open `https://paite.lamkalabs.com`. Answer 5 sentences, skip 1, give a name when asked.
2. On a second phone, answer 2 of the same English sentences if they appear (they appear only while they have fewer than 2 answers).
3. Reviewer opens `https://paite.lamkalabs.com/review`, signs in with the emailed code, and reviews 5 cards: at least one Accept, one Fix, one Reject.
4. Next morning: a new file `community/verified-*.jsonl` exists in the dataset repo, the "Check data" workflow is green, and `training/parallel.jsonl` has `"source": "community"` rows after `python scripts/build_training.py`.
5. A stranger email at `/review` sees Cloudflare's "not allowed" page.

- [ ] **Step 10: Commit any fixes from the launch check, then tag**

```bash
git tag v1.0.0 && git push --tags
```

---

## Layer 2: DeepSeek (outline; plan in detail after layer 1 is live)

- **Task 9: Pre-review notes.** Cron `*/15 * * * *`. Select answers with `ai_note IS NULL` (limit 50). One DeepSeek `deepseek-chat` call per sentence with all its answers, JSON output `{answer_id, note, flag}` where `flag ∈ {ok, tedim_style, english, junk}`. The system prompt states the Tedim/Bible-style markers (`nong`, `hiam`, `zong`, final `hi`) from `grammar_notes.md`. On any API error, leave `ai_note` NULL. Secret `DEEPSEEK_API_KEY`. The review queue order becomes: agreeing answers, then disagreements, then flagged. Tests mock the DeepSeek fetch.
- **Task 10: Daily refill.** Cron `0 2 * * *`. If `count(open) < 300`, request 50 simple everyday English sentences for the topic of the day (rotation: home, market, church, farming, school, health, weather, travel, family, feelings). Insert with `source = 'deepseek'` and `INSERT OR IGNORE` on `english_key`. Reviewers' "Retire sentence" covers bad sentences.
- **Task 11: Failure email.** Enable Email Routing on `lamkalabs.com`, verify the owner's address, add a `send_email` binding. After a failed `job_runs` row, if the previous row of the same job also failed, send one email.

## Layer 3: Delight (outline)

- **Task 12: Share to WhatsApp Status.** After 5 answers, draw a 1080×1920 canvas image (puandum band, "I helped write Paite into the future: N sentences", the link), and share it with `navigator.share({ files })` when supported, or offer it as a downloadable image.
- **Task 13: Contributors page.** The nightly export also writes `CONTRIBUTORS.md` to the dataset repo and the app serves `/contributors` from D1: named contributors and reviewer display names with counts.
- **Task 14: Badges and rankings.** Weekly and all-time rankings for contributors (by verified answers) and reviewers (by decisions), with badges at 10, 50, 100, 500. Phone-based identity stays; a name is needed to appear on the board.

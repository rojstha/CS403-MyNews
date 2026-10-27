# My News: CS 403 (Flutter + AI + Server)

My News groups different publishers' coverage of the same event into one story, adds background links, and shows a stored AI analysis with traceable perspectives. A server does all collection, grouping and AI work once per hour; the Flutter Android app only reads the stored results.

**Deployed API:** `PENDING: https://<your-service>.onrender.com` · **APK:** `flutter_app/build/app/outputs/flutter-apk/app-release.apk` (build command below)

## Architecture

```
 RSS feeds (Fox, NPR, BBC, Guardian,     Wikipedia API        Anthropic API
 Al Jazeera, CBS, PBS)                         │              (claude-opus-5-5)
          │                                    │                     │
          ▼                                    ▼                     ▼
 ┌──────────────────────── Hourly worker (Render Cron Job, python -m app.worker) ─────────────────┐
 │ fetch feeds → normalize + dedupe by URL → expire >168 h → group into stories → clean orphans   │
 │ → background links → (re)generate AI analysis only when its input fingerprint changed → log run│
 └───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                 ▼
                                   PostgreSQL (persistent, UTC timestamps)
                                                 ▲
                                                 │ read only
                         FastAPI web service: GET /stories, /stories/{id}, /status
                                                 ▲
                                                 │ HTTPS JSON
                          Flutter Android app (+ optional offline cache on the phone)
```

Why this shape: many readers reuse one stored result. Opening the app, refreshing, or pressing the AI button never starts a feed download or an AI call; it reads the database. Secrets (database URL, AI key, admin token) exist only in the server environment.

## Repository layout

| Path | Contents |
|---|---|
| `backend/app/` | FastAPI API (`main.py`), worker entry (`worker.py`), pipeline (`pipeline.py`), `ingest/` feeds, `grouping/`, `background/`, `ai/` |
| `backend/prompts/summary_system.md` | AI system prompt (versioned; model config in `docs/METHODS.md` §5 and `.env.example`) |
| `backend/migrations/` | Alembic database migrations |
| `backend/tests/` | 31 pytest tests + labelled fixture dataset |
| `flutter_app/lib/` | Flutter client: `data/repository.dart` (API + cache), `models.dart`, `ui/` screens |
| `flutter_app/test/` | 17 repository and widget tests |
| `render.yaml` | Deployment: web service, hourly cron job, Postgres |
| `starter/` | The course starter (reference only) |
| `docs/` | API, methods, verification, AI review, release notes + defect log, deploy, presentation, reflection |

## Setup

Backend and app commands are in [docs/DEPLOY.md](docs/DEPLOY.md). Short version:

```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && .venv/bin/alembic upgrade head
.venv/bin/python -m app.worker --trigger manual && .venv/bin/uvicorn app.main:app --port 8000
.venv/bin/python -m pytest

cd ../flutter_app && flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://<your-api>
```

## Data model

| Table | Key fields |
|---|---|
| `articles` | `id` = sha1(normalized URL), unique `normalized_url`, `url`, `publisher`, `title`, `excerpt` (publisher's feed text), `published_at`, `first_seen_at`, `last_seen_at`, `story_id` |
| `stories` | `id` (stable 16-hex), `headline`, `created_at`, `updated_at`, `background_signature` |
| `summaries` | one per story: `status`, `content` (JSON), `input_article_ids`, `input_fingerprint`, `provider`, `model`, `prompt_version`, `generated_at`, `version`, `error` |
| `background_resources` / `story_background` | Wikipedia page (url, title, description) and its link to a story with the matched term and rank |
| `collection_runs` | one per run: trigger, start/finish, status, feed/article/story/summary counts, short errors (no article text) |

## API

`GET /stories`, `GET /stories/{id}`, `GET /status`, `GET /health`, protected `POST /admin/collect`. Full contract with examples: [docs/API.md](docs/API.md).

## Methods

Grouping, retention and missing-date policy, background selection, and AI generation/validation/reuse are explained in [docs/METHODS.md](docs/METHODS.md). In brief:

- **Grouping:** TF-IDF similarity of headline + excerpt, within 72 h, ≥2 shared distinctive terms, plus a whole-story similarity check; one shared name is not enough. It can split an event described in different words, or merge two very similar same-place events.
- **Retention:** 168 h by publication time; items with missing/invalid/future dates are skipped, never given the download time; expired articles are hidden by the API immediately and deleted each run, along with empty stories, their summaries and unused background links.
- **AI:** structured JSON, every claim cited to input articles, citations validated server-side, "Insufficient evidence for distinct perspectives" when warranted, regenerated only when inputs change, honest `failed`/`outdated` states.

## Services, costs and quotas

| Service | Use | Expected cost |
|---|---|---|
| Render web service | API | Free plan (sleeps after ~15 min idle; first request can take up to a minute). Starter plan keeps it awake for a monthly fee. |
| Render cron job | hourly worker | Cron jobs are billed by running time on a paid instance type; each run takes about 10–60 s. Check Render's current pricing. |
| Render PostgreSQL | storage | Free for 30 days, then a paid basic plan. Data is small (a few MB). |
| Anthropic API | story analysis | Pay per token. Opus 5.5 costs $4 / $20 per million input/output tokens; one analysis is roughly 1.5 k input + 1–4 k output tokens (including reasoning), so around $0.03–0.09 each. Controlled by `AI_MAX_SUMMARIES_PER_RUN`, `AI_MIN_PUBLISHERS`, `AI_MODEL`, `AI_EFFORT`. Unchanged stories cost nothing. |
| Publisher RSS, Wikipedia API | sources | Free; Wikipedia requires a contact User-Agent (`CONTACT_INFO`). |

## Known limitations

- AI analysis uses headlines and feed excerpts only, so it can miss context or misstate details; it is labelled and cited, and original links are one tap away.
- Grouping is lexical (no semantic understanding); see METHODS for failure cases.
- Background links come only from English Wikipedia exact-title matches; some stories have none.
- Free hosting sleeps; free Postgres expires after 30 days.
- The release APK is debug-signed (class beta only).

## Release notes and defect log

See [docs/RELEASE.md](docs/RELEASE.md). Verification evidence: [docs/VERIFICATION.md](docs/VERIFICATION.md). Presentation: [docs/PRESENTATION.md](docs/PRESENTATION.md). AI reflection: [docs/AI_REFLECTION.md](docs/AI_REFLECTION.md).

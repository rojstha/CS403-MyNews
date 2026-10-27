# My News: CS 403 (Flutter + AI + Server)

My News groups different publishers' coverage of the same event into one story, adds background links, and shows a stored AI analysis with traceable perspectives. A server does all collection, grouping and AI work once per hour; the Flutter Android app only reads the stored results.

**Deployed API:** `PENDING: https://<your-service>.onrender.com` · **APK:** `flutter_app/build/app/outputs/flutter-apk/app-release.apk` (build command below)

## Architecture ($0 deployment)

```
 RSS feeds (Fox, NPR, BBC, Guardian,          Wikipedia API
 Al Jazeera, CBS, PBS)                              │
          │                                         │
          ▼                                         ▼
 cron-job.org ──:00 hourly POST /admin/collect?trigger=scheduled──► Render free web service (FastAPI)
 (also GET /health every 10 min: keeps it awake)   • collects feeds, dedupes, expires >168 h,
                                                     groups stories, finds background links
                                                   • serves GET /stories, /stories/{id}, /status
                                                          │  ▲
                                                 writes   ▼  │ reads
                                            Neon free PostgreSQL (persistent, UTC)
                                                          ▲  │
                                       writes summaries   │  ▼ reads stories needing AI
                                 Mac: launchd :05 hourly → python -m app.ai_worker → Ollama (granite4.2:3b, local)

 Flutter Android app ──HTTPS──► Render API   (read-only; optional offline cache on the phone)
```

Why this shape: every reader reuses one stored result. Opening the app, refreshing, or pressing the AI button never starts a feed download or an AI call; it reads the database. The cloud server never runs AI (`AI_PROVIDER=none`); the free local model on the developer's Mac writes summaries into the shared database, so the API stays public while the AI costs nothing. Secrets (database URL, admin token) exist only in Render's dashboard and the Mac's git-ignored `backend/.env`.

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

## Services, costs and quotas (total: $0)

| Service | Use | Free-plan limits |
|---|---|---|
| Render free web service | public API + collection | No card required. 750 instance hours/month (keep-awake pings use ≤744), 512 MB, may restart at any time; without a card, overages suspend instead of charging. |
| Neon Postgres Free | database | No card, permanent. 1 GB/project, 100 compute-hours/month, compute sleeps after 5 idle minutes; overages suspend/block, never charge. |
| cron-job.org | hourly trigger + keep-awake | Free (donations). 30 s request timeout; job disabled after >25 failures. |
| Ollama + granite4.2:3b on the Mac | AI summaries | Free, open model (2.2 GB). ~30–90 s per summary on an 8 GB M3; at most 10 per hour, stories with 2+ publishers only. Mac must be on and awake. |
| Publisher RSS, Wikipedia API | sources | Free; Wikipedia requires a contact User-Agent (`CONTACT_INFO`). |

The Anthropic provider is still supported (`AI_PROVIDER=anthropic`) but not used, because it is paid.

## Known limitations

- AI analysis uses headlines and feed excerpts only, so it can miss context or misstate details; it is labelled and cited, and original links are one tap away.
- Grouping is lexical (no semantic understanding); see METHODS for failure cases.
- Background links come only from English Wikipedia exact-title matches; some stories have none.
- AI summaries only appear while the Mac is on, awake and online; a small 3B model is less faithful than large paid models, so its output is labelled, cited, validated and manually reviewed.
- Free hosting may restart at any time; if Render restarts during a collection, that run is marked failed and the next hourly run repairs it.
- The release APK is debug-signed (class beta only).

## Release notes and defect log

See [docs/RELEASE.md](docs/RELEASE.md). Verification evidence: [docs/VERIFICATION.md](docs/VERIFICATION.md). Presentation: [docs/PRESENTATION.md](docs/PRESENTATION.md). AI reflection: [docs/AI_REFLECTION.md](docs/AI_REFLECTION.md).

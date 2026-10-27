# Deploying My News

## Backend on Render (recommended)

`render.yaml` creates three things from one repository:

| Resource | Role | Plan in file |
|---|---|---|
| `mynews-db` | PostgreSQL, persistent across restarts | free (expires after 30 days; upgrade to basic to keep) |
| `mynews-api` | FastAPI web service the app reads | free (sleeps when idle) |
| `mynews-hourly-collect` | Cron job: `python -m app.worker --trigger scheduled` at minute 0 every hour (UTC) | starter (cron jobs are not free) |

The cron job is a separate process from the API, so collection happens even when nobody has the app open. Both run `alembic upgrade head` first, so the schema is created and migrated automatically.

Steps:

1. Push this repository to GitHub (private is fine).
2. Render dashboard → **New → Blueprint** → select the repository → Render reads `render.yaml`.
3. When prompted, enter the secret values: `ANTHROPIC_API_KEY` (on both services) and `CONTACT_INFO` (e.g. your repository URL; Wikipedia requires a URL or email).
4. Apply. Wait for the API to show **Live**; open `https://<api>.onrender.com/health`.
5. Trigger the first collection without waiting for the hour: copy `ADMIN_TOKEN` from the API service's Environment tab, then
   `curl -X POST -H "X-Admin-Token: <token>" https://<api>.onrender.com/admin/collect`, wait 1–3 minutes, and check `/status`.
   (Or press **Trigger Run** on the cron job's page.)
6. After two hours, `/status` should list two runs with `"trigger": "scheduled"` about an hour apart. Screenshot this and the cron job's run history for the evidence file.

## Local development

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # edit values; SQLite by default
.venv/bin/alembic upgrade head
.venv/bin/python -m app.worker --trigger manual     # one collection
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m pytest
```

## Flutter app

```bash
cd flutter_app
flutter test
flutter build apk --release --dart-define=API_BASE_URL=https://<api>.onrender.com
# output: build/app/outputs/flutter-apk/app-release.apk
```

Install on the phone: enable Developer options → USB debugging, connect by USB, then `flutter install --release`, or copy the APK to the phone and open it (allow "install unknown apps"). Against a local server from the Android emulator use `--dart-define=API_BASE_URL=http://10.0.2.2:8000` with a debug build.

The release APK is signed with the debug key (fine for a class beta; not for the Play Store).

## Free alternative for the scheduler

If you do not want a paid Render cron job, the same command can run from a GitHub Actions schedule against the database URL (store it as a repository secret). GitHub may delay scheduled workflows by several minutes under load and disables them after 60 days without repository activity, so record the actual run times as evidence.

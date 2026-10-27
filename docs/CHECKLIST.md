# Requirements checklist

✅ done and verified · 🟡 implemented, needs live verification · ⛔ blocked on you (account, key, phone)

| PDF § | Requirement | Where | Status |
|---|---|---|---|
| 1 | Server collects, groups, summarizes; app only reads | `backend/app/pipeline.py`, `flutter_app/lib/data/repository.dart` (only `/stories` calls; test asserts this) | ✅ |
| 1 | Deployed internet-accessible backend, persistent storage | `render.yaml`, Alembic migrations | ⛔ needs Render account |
| 1 | Credentials only on server; `.env.example` | `backend/.env.example`, `.gitignore`; app has no keys | ✅ |
| 2.1 | ≥3 distinct publishers | 7 publishers, 13 feeds; live run 13/13 feeds OK | ✅ |
| 2.2 | Hourly schedule independent of clients; protected manual trigger | Render cron `0 * * * *`; `POST /admin/collect` with token (401 verified) | 🟡 config done; ⛔ needs deploy for run evidence |
| 2.3 | Duplicate prevention | normalized URL + sha1 id; tests + live rerun | ✅ |
| 2.4 | 7-day window by publication time, API excludes between runs, date policy documented | `cutoff()`, read-time filters, `docs/METHODS.md` §2 | ✅ |
| 2.5 | Cleanup of empty stories, summaries, background; rebuild affected summaries | `cleanup_orphans`, `invalidate_dependent_summaries`; tests | ✅ |
| 2.6 | Failure isolation, last successful collection time, run records | per-feed try/except, `collection_runs`, `/status`; tests | ✅ |
| 3 | Automatic grouping, not single keyword; stable IDs; joins; single-source kept | `grouping/grouper.py`; tests; live 18 multi-publisher groups | ✅ |
| 3 | 5 multi-publisher examples + 2 separate | `docs/VERIFICATION.md` (live) + fixtures | ✅ |
| 3 | Explain method + a failure case | `docs/METHODS.md` §3 | ✅ |
| 4 | Native Flutter Android app | `flutter_app/`; release APK builds | ✅ build; ⛔ phone run |
| 4 | List: headline, latest time, publisher count, refresh, loading/empty/error | `story_list_screen.dart`; widget tests | ✅ |
| 4 | Detail: publisher buttons only for covering outlets, background, AI overview + perspectives | `story_detail_screen.dart`, `ai_analysis_screen.dart`, `perspective_screen.dart`; widget tests | ✅ |
| 4 | Background for ≥3 stories; "No background resource available" | live examples in VERIFICATION; widget test | ✅ |
| 4 | Original vs AI wording distinguishable | excerpt labelled "original wording, not the full article"; AI badge | ✅ |
| 5 | Real AI model, overview, agreement/disagreement/uncertainty, ≥2 perspectives when supported | `ai/provider.py`, `prompts/summary_system.md` | 🟡 code + fake-model tests; ⛔ needs API key for real output |
| 5 | Traceability, AI label, timestamp, excerpt-only disclosure | `summarize.validate_output`, API fields, UI | ✅ |
| 5 | Stored and reused; regenerate on input change/expiry; no AI call on read | fingerprint; tests | ✅ |
| 5 | Prompt + model config saved | `backend/prompts/`, `.env.example`, `render.yaml`, METHODS §5 | ✅ |
| 5 | Manual check of 3 summaries | `docs/AI_REVIEW.md` worksheet | ⛔ needs real summaries |
| 5 | ≥3 stories with real contrasting perspectives | | ⛔ needs real summaries |
| 6 | Documented list + detail endpoints | `docs/API.md` | ✅ |
| 6 | Optional cache: sync time, offline label, hide expired | repository + tests | ✅ |
| 8 | Release notes, defect log, regression runs | `docs/RELEASE.md` | ✅ notes/log; ⛔ 3 phone runs |
| 9 | README with diagram, data model, costs, limitations | `README.md` | ✅ (fill deployed URL) |
| 9 | Presentation via Phone Link | `docs/PRESENTATION.md` | ⛔ you |
| 9 | Verification evidence | `docs/VERIFICATION.md` | 🟡 pending items marked |
| 9 | AI reflection | `docs/AI_REFLECTION.md` draft | ⛔ your edits |

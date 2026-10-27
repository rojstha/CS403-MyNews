# Requirements checklist (updated 2026-10-27)

✅ done and verified · 🟡 done with a documented limitation · ⏳ waiting for time to pass · ❌ not done / needs the student

| PDF § | Requirement | Evidence | Status |
|---|---|---|---|
| 1 | Server does collection, grouping, AI; app only reads | Render API `AI_PROVIDER=none`; app calls only `/stories` (test asserts it) | ✅ |
| 1 | Internet-accessible backend, persistent storage | https://mynews-api-mq6m.onrender.com + Neon Postgres | ✅ |
| 1 | Secrets only on server; `.env.example` | Render dashboard + git-ignored `backend/.env`; secret-scan before every commit; deploy-config tests | ✅ |
| 1 | $0 cost | Render free web, Neon Free, cron-job.org, local Ollama | ✅ |
| 2.1 | ≥3 publishers | 7 publishers, 13/13 feeds in deployed runs | ✅ |
| 2.2 | Hourly automatic collection, protected manual trigger | cron-job.org → `POST /admin/collect?trigger=scheduled` (token header); run #3 at 15:00 UTC | ⏳ one automatic run recorded; record the 16:00 run as the second |
| 2.3 | No duplicates | tests + live re-runs (0 new on unchanged feeds) | ✅ |
| 2.4 | 7-day window by publication time; date policy | tests; `docs/METHODS.md` §2 | ✅ |
| 2.5 | Cleanup + summaries never depend on removed articles | tests | ✅ |
| 2.6 | Failure isolation, last success time, run log | tests; `/status` | ✅ |
| 3 | Grouping (5 multi-publisher + 2 kept-separate examples, failure case) | `docs/VERIFICATION.md`, `docs/METHODS.md` §3 | ✅ |
| 4 | Flutter Android app: list, detail, buttons, states | release APK tested on emulator; 17 widget/repository tests | ✅ |
| 4 | Background for ≥3 stories; "No background resource available" | live: Ukraine ceasefire (Melania Trump, Oleshky, Ukraine), Illinois, RAF Fairford, …; widget test | ✅ |
| 4 | **Physical phone via Phone Link** | no Android phone available; emulator used | ❌ ask instructor / borrow a phone |
| 5 | Real AI model, stored and reused | `granite4.2:3b` via Ollama; 20/20 multi-publisher stories ready; no AI call on read | ✅ |
| 5 | ≥3 stories with contrasting perspectives | Comey, Jordan, Ukraine ceasefire have perspectives; ceasefire's are invented | 🟡 2 genuinely supported, 1 flawed |
| 5 | Traceability, AI label, timestamp, excerpt disclosure | all screens; 10/10 citation check | ✅ |
| 5 | Prompts + model config in repo | `backend/prompts/`, `.env.example`, `docs/METHODS.md` §5 | ✅ |
| 5 | Manual check of 3 summaries | `docs/AI_REVIEW.md` (draft) | 🟡 student must verify and sign off |
| 5 | Hourly AI worker on schedule | launchd at :05; runs #5/#6 exit 0; overlap blocked | ⏳ record the first automatic 16:05 run |
| 6 | Documented API; offline cache | `docs/API.md`; emulator offline test | ✅ |
| 8 | Release notes, defect log, regression runs | `docs/RELEASE.md`: 1 emulator run passed; D11 (AI quality) open | 🟡 2 more runs; D11 open means not fully beta-ready |
| 9 | README, verification, screenshots | `README.md`, `docs/VERIFICATION.md`, `docs/screenshots/` | ✅ |
| 9 | Presentation (5–7 min) | `docs/PRESENTATION.md` | ❌ student: rehearse/record |
| 9 | AI development reflection | `docs/AI_REFLECTION.md` draft | ❌ student: write ✏️ parts |
| — | Push latest changes to GitHub; redeploy Render for the `/status` fix | local commit ready | ❌ needs approval |

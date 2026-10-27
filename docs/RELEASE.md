# Release notes: My News 1.0.0 (beta)

## Features

- Top stories: one card per event with headline, latest article time, and number of distinct publishers; newest first; last seven days; refresh, pull-to-refresh, source and day filters.
- Story detail: overview, one button per publisher that covered the story (article chooser when a publisher has several), background reference links, AI analysis entry.
- AI analysis: AI-generated overview, agreement / differences / uncertainty, named perspectives with cited claims, supporting articles, generation time and model, input-scope disclosure.
- Honest states: loading skeletons, empty and error screens with retry, offline mode showing saved stories (expired news hidden), "outdated", "unavailable" and "Insufficient evidence for distinct perspectives" messages.
- Server: hourly collection from 7 publishers, duplicate prevention, 7-day retention, automatic grouping, Wikipedia background, stored AI analysis reused by every reader.

## Known minor issues

- Grouping can occasionally split one event into two stories (e.g. the Israeli election on 2026-10-27). Cosmetic: both stories remain correct and fully sourced.
- On the free hosting plan the first request after ~15 idle minutes can take up to a minute while the server wakes; the app shows its loading state and allows retry.
- New single-source stories may show "AI analysis has not been generated yet" for up to a few hours because generation is capped per run to control cost.

## Service limitations

- AI analysis is based on headlines and RSS excerpts only, not full articles, and can contain mistakes. Readers should use the publisher buttons for full context.
- Publisher and Wikipedia pages open in the browser and need an internet connection; some publishers may show paywalls or cookie banners.
- Background links come from English Wikipedia only.

## Reporting problems

Beta testers: use About → Report a problem in the app (set `FEEDBACK_EMAIL` at build time), or the course issue tracker. Include the story headline, what you tapped, what you expected, and a screenshot.

## Defect log

Severity: **Critical** = crash, data loss, exposed secret · **Major** = required feature broken · **Minor** = cosmetic/workaround exists.

| ID | Severity | Found | Steps to reproduce | Fix | Status / verification |
|---|---|---|---|---|---|
| D1 | Major | 2026-10-27, fixture tests | Ingest the Comey indictment and the Comey-daughter ruling together → merged into one story | Raised pair threshold 0.30→0.35; added story-average similarity rule (anti-chaining); IDF smoothing | Fixed. `test_related_topics_remain_separate_stories` passes; live run keeps them separate |
| D2 | Major | 2026-10-27, live run | Run worker → every Wikipedia request returns 403 "respect our robot policy"; no background links | User-Agent without contact info; removed library suffix and made `CONTACT_INFO` (URL/email) a documented required setting | Fixed. Live run produced links for 16 of 18 multi-publisher stories |
| D3 | Major | 2026-10-27, unit tests | Group with only 3 articles on one event → articles not grouped (IDF too flat in small corpora) | IDF pseudo-document smoothing | Fixed. All 31 backend tests pass |
| D4 | Minor | 2026-10-27, widget tests | Story detail "Story overview" row overflows 30 px with wide text | Title made flexible | Fixed. 1.5× text-size test passes |
| D5 | Minor | 2026-10-27, widget tests | Perspective screen badge overflows 83 px at large text | Badge text made flexible | Fixed. 1.5× text-size test passes |
| D6 | Minor | 2026-10-27, review | A manual and a scheduled run could overlap | Worker skips when a run started < 50 min ago is still running | Fixed. Verified locally (`skipped: true`) |

| D7 | Major | 2026-10-27, launchd install | Install the hourly AI job while the project is in ~/Downloads → `Operation not permitted`, exit 126, no summaries | macOS privacy blocks background jobs in Downloads; project moved to ~/Projects/myNews, venv rebuilt, job reinstalled | Fixed. launchd runs #5 and #6 exit 0, empty error log |
| D8 | Minor | 2026-10-27, deployed `/status` | `/status` showed `ai_model: claude-opus-5-5` although the server runs no AI | `/status` now reports `ai.provider_on_this_server` and the model that actually wrote the latest summary | Fixed locally + test; live after the next Render deploy |
| D9 | Minor | 2026-10-27, emulator | List footer said "20 storys" | Irregular plural support | Fixed; widget test checks "2 stories" |
| D10 | Minor | 2026-10-27, emulator | AI screen: model name wrapped onto its own line starting with "·" | Date and model joined into one label | Fixed in rebuilt APK |
| D11 | Major (AI quality) | 2026-10-27, manual review | Ukraine-ceasefire analysis invents "Supporters/Critics" viewpoints; Jordan analysis misreads two casualty counts | Prompt v3 tested and rejected (worse); limitation disclosed in app labels, README and AI_REVIEW.md | **Open, mitigated**: limit of the free 3B model |

Environment notes (not app defects): the emulator's Wi-Fi sometimes stays "connecting" after boot (fix: `adb shell svc wifi disable && adb shell svc wifi enable`); pasting the Neon string in TextEdit removed the following lines of `backend/.env` (DEPLOY.md now includes a check).

Add any defect found during phone testing here. The release is beta-ready only when no Critical or Major row is open.

## Core-workflow regression run sheet

Core workflow: launch → stories load → open a multi-publisher story → tap two publisher buttons (browser opens correct article) → back → tap a background link → back → open AI analysis → open a perspective → back to analysis → back to story → back to list → refresh.

| Run | Date | Build (version / API URL) | Device / Android | Result | Notes |
|---|---|---|---|---|---|
| 1 | 2026-10-27 | 1.0.0 release APK / https://mynews-api-mq6m.onrender.com | Android Emulator Pixel_4, Android 17 (arm64) | pass | list, 2+ filter, publisher filter, empty state, story detail, Fox News link opened original, back preserved story, background links, AI analysis, perspective + switch, back ×3, offline banner, retry recovered |
| 2 | | | | | |
| 3 | | | | | |

Also record once: airplane mode on → app shows offline banner with saved stories → airplane mode off → Retry loads live data.

# Verification evidence

Status legend: **PASS** = verified with the evidence shown · **PENDING** = needs the deployed service, the AI key, or the physical phone (fill in when done). Nothing marked PASS was assumed.

How to re-run the automated checks:

```bash
cd backend && .venv/bin/python -m pytest -v        # 31 tests
cd flutter_app && flutter test                      # 17 tests
```

## Required checks (PDF section 10)

| Check | Expected result | Evidence | Result |
|---|---|---|---|
| Repeated ingestion | Identical inputs twice do not duplicate articles or stories | `test_repeated_ingestion_does_not_duplicate`, `test_tracking_parameters_do_not_create_duplicates`. Live: 3 consecutive local runs on 2026-10-27 → run 1 `articles_new=283, stories_created=249`; runs 2–3 `articles_new=0, stories_created=0` | PASS |
| Same event, different publishers | One story with working publisher buttons | `test_five_multi_publisher_events_each_form_one_story`, `test_same_event_from_publishers_is_one_story_with_correct_sources`; live examples below; Flutter `detail shows only covering publishers…` | PASS (server, widget tests, Android emulator 2026-10-27: Fox News button opened the matching foxnews.com article) |
| Similar topic, different events | Unrelated events stay separate | `test_related_topics_remain_separate_stories`, `test_one_shared_name_is_not_enough`; live examples below | PASS |
| Hourly automation | Deployed config + ≥2 consecutive scheduled runs without client activity | cron-job.org calls `POST /admin/collect?trigger=scheduled` at :00 UTC; `GET /status` on the deployed API: run #1 14:46:50 (console test run), **run #3 15:00:04 scheduled, success, 13/13 feeds, 30 s**; next: 16:00 | PASS for one automatic hourly run; second consecutive automatic run to be recorded at 16:00 UTC |
| Seven-day boundary | Expired articles leave the API and are deleted; recent remain | `test_seven_day_boundary` (167 h article hidden by API 2 h later before cleanup, deleted on next run; 200 h article never stored), `test_missing_and_future_dates_are_skipped` | PASS |
| Source expiration inside a group | Expired source button disappears, summary no longer depends on it | `test_source_expiration_inside_group_regenerates_summary` (BBC disappears, summary v2 excludes its ID), `test_summary_citing_expired_article_is_never_served`; Flutter `offline detail drops expired sources…` | PASS |
| Shared AI output | Repeated reads by two clients reuse the stored version, no new generation | `test_shared_ai_output_is_reused` (two API clients × 2 reads → same `version`/`generated_at`; model call count stays 1; unchanged next run → still 1). Live: compare `summary.version` from two phones + `total_ai_generations_logged` before/after | PASS (automated). Live: summaries are written once by the AI worker (`ai` runs in `/status`) and every reader gets the same stored `version`/`generated_at`; the Render API never calls a model (`AI_PROVIDER=none`) |
| Provider failure | Unavailable feed or AI → clear status, stored stories still usable | `test_feed_outage_keeps_valid_stories`, `test_all_feeds_down_marks_run_failed_but_serves_data`, `test_ai_failure_gives_honest_status`, `test_ai_provider_missing_does_not_crash_run`, `test_background_failure_keeps_stories`. Live: with no AI key, run status `partial`, 25 summaries `failed`, stories served with "AI analysis is currently unavailable…" | PASS |
| Client connectivity failure | Retry state or labelled cached content | Flutter `error state with retry recovers`, `offline: serves cache, labels it, and hides expired articles`, `no cache and no network gives a readable error`, `server errors become friendly messages` | PASS (automated + emulator: network off → "Offline: showing stories saved … Expired stories are hidden" with Retry; network on → Retry loaded live data) |
| Physical-phone presentation | Release build on phone via Phone Link | — | NOT POSSIBLE AS SPECIFIED: no Android phone available. Release APK tested on the Android Emulator (Pixel_4, Android 17, arm64) instead; see note below |
| Beta-readiness regression | 3 consecutive core-workflow passes; no open critical/major defects | Run sheet in `docs/RELEASE.md` | PARTIAL: 1 full core-workflow run on the emulator, no blocking defect; 3 consecutive runs still to record (`docs/RELEASE.md`) |
| Source fidelity | Excerpts stay original; AI claims traceable | Excerpts stored verbatim (HTML stripped) and labelled `publisher_feed_excerpt` / "original wording, not the full article"; AI citations validated (`test_citations_are_validated_against_inputs`, `test_detail_has_traceable_ai_labels`); prompt-injection containment `test_article_text_is_data_not_markup` | PASS for excerpts and citation validity (10/10 live summaries cite only their own articles). Manual review (`docs/AI_REVIEW.md`) found unsupported AI claims in 2 of 3 summaries; documented limitation of the free 3B model |

Other checks: admin trigger rejects missing/wrong token (`test_admin_collect_requires_token`, and live `401` from local server); worker skips if a run is in progress (verified locally: `{"skipped": true, "reason": "run 4 still running"}`); all screens lay out without overflow at 1.5× text on a 360 dp phone (`every screen lays out without overflow at 1.5x text size`); real API JSON parsed by the app's models (one-off contract check against live data, 249 stories).

## Grouping examples (live data, local collection 2026-10-27 ~12:50 UTC)

Five stories with two or more publishers:

| # | Story | Publishers |
|---|---|---|
| 1 | Third federal prosecution of former FBI Director James Comey | NPR, BBC News, The Guardian, CBS News, PBS NewsHour |
| 2 | Two men charged over alleged plot to assist Iran (RAF Fairford) | BBC News, The Guardian, Al Jazeera, CBS News |
| 3 | Lula elected to a fourth term in Brazil | NPR, BBC News, The Guardian |
| 4 | Jordan strikes Syria in retaliation for church attack | BBC News, The Guardian, Al Jazeera |
| 5 | María Corina Machado returns to Venezuela | Fox News, BBC News, CBS News |

Also grouped in the same run: Jay-Z Super Bowl halftime (NPR, BBC, CBS), judge rules Comey's daughter illegally fired (Fox, NPR, BBC), Brewers–Rays World Series (NPR, Guardian), Harry Kane Ballon d'Or (NPR, BBC), Serbia election (BBC, PBS) and others: 18 multi-publisher stories in total, none with a visible wrong merge on manual inspection.

Two related topics kept separate:

| Pair | Why they must stay apart | Result |
|---|---|---|
| "Trump administration charges former FBI Director James Comey for the third time" vs "Judge rules DOJ illegally fired James Comey's daughter" | Same person and same department, different events | Two stories (5 and 3 publishers) |
| "Netanyahu faces first national election since Oct. 7" vs "MPs detained by Israel and barred from entering West Bank" | Same country and days, different events | Two stories |

Known grouping miss in the same run: the Israeli election was split into two stories (see `docs/METHODS.md`).

The same cases are reproduced deterministically by the **fixture dataset** `backend/tests/fixtures/events.py` (clearly labelled test-only data modelled on these headlines).

## Background examples (live, same run)

| Story | Background links shown |
|---|---|
| RAF Fairford charges | RAF Fairford · Iran |
| Comey's daughter ruling | Maurene Comey · James Comey |
| Lula re-election | Flávio Bolsonaro · Luiz Inácio Lula da Silva · Brazil |
| Brewers–Rays | World Series · Tampa Bay Rays |
| Machado return | María Corina Machado · Venezuela |
| Washington noncitizen ballots | none → "No background resource available" |

## Manual review of three AI summaries

Done (draft for the student to verify): `docs/AI_REVIEW.md`. Comey: acceptable. Jordan: valid perspectives, 2 unsupported claims. Ukraine ceasefire: invented Supporters/Critics viewpoints. A prompt fix (v3) was tested and rejected because it made results worse.

## Deployment evidence

Deployed 2026-10-27.

| Item | Value |
|---|---|
| API URL | https://mynews-api-mq6m.onrender.com |
| `GET /health` | `{"ok":true,...}` (checked 14:49 UTC) |
| Database | Neon free Postgres (AWS us-east-2); 284 articles / 251 stories after first run |
| Scheduled collection runs (`GET /status`) | #1 14:46:50 test run, success, 284 new · #3 15:00:04 scheduled, success, 13/13 feeds, 5 new |
| AI worker runs (`trigger: ai`) | #2 14:56 manual: 10 generated, 0 failed, 365 s · #4 by hand: 10 more · #5, #6 via launchd: success, nothing to do (all 20 multi-publisher stories ready) |
| Overlap protection | launchd run #6 active → second worker printed `{"skipped": true, "reason": "AI run 6 still running"}`; second `launchctl kickstart` did not start another copy |
| Public API after AI | 20/20 multi-publisher stories `summary_status: ready`, model `granite4.2:3b` |

**Physical phone:** the PDF requires a physical Android phone shown through Microsoft Phone Link. The student does not own one, so the release APK was verified on the Android Emulator instead. Ask the instructor whether an emulator demo is acceptable or borrow an Android phone for the presentation; the same APK installs unchanged.

Screenshots from the emulator are in `docs/screenshots/` (story list, filters, story detail, publisher link opening the original article, AI overview, background links, AI analysis, perspectives, offline mode, empty-filter state).

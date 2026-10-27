# My News API

Base URL: the deployed Render service (see README, "Deployed service").
All timestamps are UTC ISO-8601 strings ending in `Z`. All endpoints are read-only except the protected admin trigger. **No endpoint fetches news or calls the AI model**; they only read what the hourly worker stored.

## GET /stories

Active stories (at least one article published in the last 168 hours), newest first.

Optional query parameters: `publisher` (only stories covered by that publisher), `hours` (1–168, only stories updated within N hours), `multi_source=true` (2+ publishers).

```json
{
  "server_time": "2026-10-27T13:00:02Z",
  "window_hours": 168,
  "ordering": "newest_first",
  "last_successful_collection_at": "2026-10-27T13:00:41Z",
  "last_run": { "id": 12, "trigger": "scheduled", "status": "success", "started_at": "...", "finished_at": "...",
                "feeds_ok": 13, "feeds_failed": 0, "articles_new": 9, "articles_expired": 4, "...": "..." },
  "publishers": ["Fox News", "NPR", "BBC News", "The Guardian", "Al Jazeera", "CBS News", "PBS NewsHour"],
  "count": 249,
  "stories": [
    {
      "id": "7ac00066cb734f3d",
      "headline": "Two men charged over alleged plot to assist Iran after RAF Fairford incident",
      "latest_published_at": "2026-10-27T10:12:00Z",
      "updated_at": "2026-10-27T11:00:40Z",
      "publisher_count": 4,
      "publishers": ["Al Jazeera", "BBC News", "CBS News", "The Guardian"],
      "article_count": 4,
      "article_dates": [{ "publisher": "BBC News", "published_at": "2026-10-26T21:04:00Z" }],
      "summary_status": "ready",
      "has_background": true
    }
  ]
}
```

`article_dates` lets an offline client remove expired articles from its cached copy and recount publishers.

## GET /stories/{id}

Full story detail. `404` if the story does not exist or all its articles have expired.

```json
{
  "id": "7ac00066cb734f3d",
  "headline": "...",
  "created_at": "...", "updated_at": "...", "latest_published_at": "...",
  "publisher_count": 4,
  "publishers": [ { "name": "BBC News", "articles": [ /* article objects, newest first */ ] } ],
  "articles": [
    { "id": "a5ace2b805abd7084311", "publisher": "BBC News", "title": "...", "url": "https://www.bbc.co.uk/news/...",
      "published_at": "...", "excerpt": "publisher's own RSS description", "excerpt_kind": "publisher_feed_excerpt" }
  ],
  "background": [
    { "title": "RAF Fairford", "url": "https://en.wikipedia.org/wiki/RAF_Fairford",
      "description": "First sentences of the Wikipedia article", "source": "Wikipedia", "matched_term": "RAF Fairford" }
  ],
  "background_status": "available",          // or "none"
  "background_message": "",                  // "No background resource available" when none
  "summary": {
    "status": "ready",                       // ready | outdated | pending | failed | not_generated
    "status_message": "",                    // human-readable explanation for non-ready states
    "label": "AI-generated",
    "generated_at": "...", "provider": "anthropic", "model": "claude-opus-5-5", "prompt_version": "v1",
    "version": 3,                            // increments on each successful regeneration
    "input_scope": "feed_excerpts",
    "input_scope_note": "Input scope: headlines and short feed excerpts only, not full articles. ...",
    "input_article_ids": ["...", "..."],
    "content": {
      "overview": "...", "overview_article_ids": ["..."],
      "agreement": "...", "disagreement": "...", "uncertainty": "...",
      "perspectives_supported": true,
      "perspectives_note": "",               // "Insufficient evidence for distinct perspectives. ..." when false
      "perspectives": [
        { "name": "Prosecutors", "summary": "...", "limits": "...", "article_ids": ["..."],
          "claims": [ { "text": "...", "article_ids": ["..."] } ] }
      ]
    }
  },
  "last_successful_collection_at": "..."
}
```

Summary status rules (enforced at read time, see `app/main.py::_summary_state`):

| status | meaning | `content` |
|---|---|---|
| `ready` | generated from exactly the current articles | present |
| `outdated` | new coverage joined after generation; every cited article still exists | present, flagged |
| `pending` | not generated yet, or an input article expired | `null` |
| `failed` | the AI call failed and no valid earlier analysis exists | `null` |
| `not_generated` | story is below `AI_MIN_PUBLISHERS` | `null` |

Text that cites an expired article is **never** returned.

## GET /status

Collection-run log, used as evidence of the hourly schedule: `runs[]` with `trigger` (`scheduled`/`manual`), `started_at`, `finished_at`, `status` (`success`/`partial`/`failed`), feed counts, article counts, stories created/removed, summaries generated/failed, and short error records (no article text). Also active article/story counts and `total_ai_generations_logged`.

## GET /health

`{"ok": true, "time": "..."}` for the host's health check.

## POST /admin/collect

Starts one collection run in the background for demonstrations. Requires header `X-Admin-Token: <ADMIN_TOKEN>`; returns `401` without it and `409` if a run is already in progress. Result appears in `GET /status`.

```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" https://YOUR-API/admin/collect
```

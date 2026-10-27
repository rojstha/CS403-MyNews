# How the server processes news

Everything here runs in the hourly worker (`python -m app.worker`, see `backend/app/pipeline.py`). The Flutter app never does any of it.

## 1. Collection and duplicates

**From the starter (`starter/app.js`):** the feed list, the parsing rules of `articleFromFeedItem()` (title, link, `pubDate`/`updated`/`published` date, description→plain text), the 7-day window and 60-minute future tolerance of `articleIsInLastSevenDays()`, and the day/source filters were moved to the server and the Flutter app. Changes: the starter fetched through public browser proxies and stored articles in each browser's local storage; here the server fetches feeds directly and stores them once for all readers. The starter's duplicate key was `feedUrl|link`, so one article listed in two feeds was stored twice and different publishers' reports were never grouped; here the key is the normalized URL, and grouping is a separate step.

- **Publishers (7):** Fox News, NPR, BBC News, The Guardian, Al Jazeera, CBS News, PBS NewsHour, via their public RSS feeds (`backend/app/ingest/sources.py`). Fox, NPR and BBC are the starter app's publishers; one publisher can have several section feeds.
- Each feed is fetched independently with a timeout. A failing feed is recorded in the run's `feed_results`/`errors` and the others continue.
- **Stable identity:** the article URL is normalized (https, lower-case host, no `www.`, no trailing slash, tracking parameters such as `utm_*`, `at_medium`, `cmpid` removed, remaining query sorted). The article ID is `sha1(normalized_url)[:20]`, and `normalized_url` is unique in the database. Re-fetching an article updates the same row (title/excerpt/date if changed); it never creates a copy. The same URL appearing in two section feeds is stored once.
- Stored per article: publisher, original title, original URL, publication time (UTC), the publisher's feed description (HTML stripped, labelled as an excerpt), first/last seen times.

## 2. Seven-day retention (by publication time)

- Window = 168 hours before "now", using the article's **publication** time, never download time.
- **Missing or invalid publication dates:** the item is skipped and counted in `articles_skipped`. We do not substitute the download time, because that would keep old articles alive and break the window. Dates more than 60 minutes in the future are treated as invalid and skipped. If a feed provides only `updated`, that date is used.
- Articles already older than 168 h when fetched are never stored.
- Every run deletes articles older than 168 h. Between runs, every API query also filters `published_at >= now − 168 h`, so an article disappears from the API the moment it expires.
- **Cleanup:** stories left without articles are deleted together with their summary and background links (database cascades). Background resources no longer linked to any story are deleted. Background pages themselves may be older than seven days.
- **Summaries:** if any article a stored summary used has been removed, the summary text is cleared immediately (`invalidate_dependent_summaries`) and regenerated from the remaining articles in the same run. The API also refuses to return text whose `input_article_ids` include a missing article.
- Operational logs (`collection_runs`) are kept longer but contain only counts and short error messages, never article bodies or summaries.

## 3. Grouping articles into stories

Goal: one story per *event*, not per topic. Implementation: `backend/app/grouping/grouper.py`.

1. Each article becomes a TF-IDF vector of its headline (weight 2) and feed excerpt (weight 1), after lower-casing, removing stop words and publisher names, and light plural stemming. IDF is computed over all articles in the 7-day window (smoothed as if at least 50 other articles exist), so words that appear everywhere ("Trump", "war", "police") count for little.
2. A new article may join an existing story only if, for at least one article already in the story:
   - the two were published within **72 hours** of each other;
   - their cosine similarity is at least **0.35**;
   - they share at least **2 distinctive terms** (words that occur in ≤4% of window articles, or multi-word capitalised names like "RAF Fairford"); one is enough only when similarity is ≥0.55;
   - and the article's **average** similarity to all of the story's articles is at least **0.25**, so a story cannot drift into a different event through one loosely related member.
3. If several stories qualify, the best-scoring one wins; otherwise the article starts a new single-source story.
4. Articles keep their story once assigned, so story IDs (random 16-hex) are stable and later coverage joins the existing story instead of creating a duplicate list entry. The headline is the article title most similar to the rest of the story.

**Why one keyword is not enough:** "James Comey" appears in both the third indictment of James Comey and the ruling on his daughter's firing. The shared name is a single distinctive term and the overall similarity of those headlines stays below the threshold, so they remain two stories (verified on live data on 2026-10-27; also covered by `tests/test_grouping.py`).

**Known mistakes the method can make:**
- *Split (false negative):* the same event described with different vocabulary can become two stories. Live example (2026-10-27): the Israeli election appeared as two stories, "Israel goes to the polls…" (Guardian, PBS) and "Netanyahu faces first national election since Oct. 7" (CBS, PBS).
- *Merge (false positive):* two different events in the same place on the same days with very similar wording (for example two separate storms hitting the same city two days apart) could be combined, because the method has no understanding of *which* event the words describe.
- Very short feed excerpts give the method little to compare.

## 4. Background resources

Implementation: `backend/app/background/wikipedia.py`.

1. Candidate terms are capitalised phrases (people, places, organisations, events) in the story's headlines and excerpts. A term must appear in a headline or in at least two articles. Generic terms (US, UK, White House, Congress, president, publisher names…) are excluded, and a single capitalised word that only starts a headline is ignored.
2. Multi-word names rank first, then terms mentioned by more articles; at most 6 are looked up.
3. Each term is looked up as an exact Wikipedia title (following redirects) through the MediaWiki API. Missing pages, disambiguation pages and pages whose final title shares no word with the term are rejected.
4. Up to 3 resources are stored per story, labelled with the Wikipedia title and the first sentences of the article. If nothing survives, the app shows **"No background resource available"**.
5. Background is recomputed only when a story's set of articles changes. A Wikipedia outage keeps the previous links.

Wikimedia requires a User-Agent with contact details; set `CONTACT_INFO` to a URL or email, otherwise Wikipedia answers `403`.

## 5. AI summaries and perspectives

Implementation: `backend/app/ai/` and the prompt in `backend/prompts/summary_system.md`.

- **Model configuration:** provider `anthropic`, model `AI_MODEL` (default `claude-opus-5-5`), adaptive thinking, `effort=AI_EFFORT` (default `medium`), structured JSON output enforced by a JSON schema (`OUTPUT_SCHEMA` in `summarize.py`), server-side refusal fallback enabled. Prompt version `v1`.
- **Input:** for each story, every active article's publisher, publication time, headline and feed excerpt, labelled A1, A2, … inside `<articles>` tags. The system prompt states that this text is untrusted data and must not be followed as instructions; `<` and `>` in article text are replaced so an article cannot close the data block.
- **Output:** overview (+ cited labels), agreement, disagreement, uncertainty, and either ≥2 perspectives (each with named group, summary, claims with cited labels, and limits) or `perspectives_supported=false` with "Insufficient evidence for distinct perspectives."
- **Validation after the model answers:** citation labels are mapped back to article IDs; citations to labels that were not in the input are dropped; claims left without a valid citation are dropped; a perspective with no supported claim is dropped; if fewer than two perspectives remain, the result becomes "Insufficient evidence for distinct perspectives."
- **Reuse:** a fingerprint (prompt version + model + every input article's id, publisher, title, excerpt, time) is stored with the summary. If it has not changed, the model is not called again. Reading a story never calls the model. Each regeneration increments `version`.
- **Regeneration:** when coverage joins, an article changes, or an input article expires, the fingerprint changes and the next run regenerates. Expired-input text is cleared immediately.
- **Failures:** a failed AI call marks the summary `failed` (or keeps a still-valid older version as `outdated`) and records the error in the run log. No fallback text is ever presented as AI output.
- **Cost guards:** at most `AI_MAX_SUMMARIES_PER_RUN` generations per run (multi-publisher stories first); optional `AI_MIN_PUBLISHERS`.

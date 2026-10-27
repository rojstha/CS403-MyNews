# Presentation script and checklist (5–7 minutes)

## Before presenting

- [ ] Phone: release APK installed, Do Not Disturb on, notifications hidden, battery > 50%, font size normal.
- [ ] Microsoft Phone Link connected and mirroring the phone screen (rehearsed at least once on the presentation computer).
- [ ] Laptop tabs open: Render dashboard (cron job run history), `https://<api>/status`, `https://<api>/stories/<id>` JSON, this repo.
- [ ] Run `/admin/collect` about 10 minutes before so stories are fresh. Pick 3 strong stories in advance (multi-publisher, background, perspectives).
- [ ] Backup: screen recording of a full run in case the network fails.

## Script

**0:00 Problem and architecture (45 s).** "Readers have to visit several sites to compare coverage. My News groups coverage of one event into one story." Show the README diagram: hourly worker → Postgres → read-only API → Flutter app. "The phone never fetches feeds or calls the AI; it only reads stored results."

**0:45 Story list on the phone (45 s).** Show Phone Link. Point out the server update time, one card per story, publisher counts, newest first. Pull to refresh: "this only asks our server for its current data."

**1:30 Grouped story (90 s).** Open a 3+ publisher story. Show the overview, then tap two publisher buttons: each opens that outlet's own article. Back. "Only publishers that actually covered this story get a button." Tap a background link (Wikipedia), back.

**3:00 AI analysis (75 s).** Open AI analysis: AI-generated label, generation time and model, agreement vs disagreement, input-scope note. Open one perspective: claims with numbered citations that open the source. Switch to the other perspective. Then show a story with "Insufficient evidence for distinct perspectives": "we don't invent opposition."

**4:15 Server and schedule (60 s).** Render dashboard: cron job running hourly. `/status`: consecutive `scheduled` runs with counts. "This ran while no one had the app open."

**5:15 Shared results (30 s).** Open the same story's JSON in the laptop browser and on the phone: same `summary.version` and `generated_at`, and `total_ai_generations_logged` does not change when we read: "a thousand readers reuse one generation."

**5:45 Reliability (45 s).** Airplane mode on the phone → offline banner and saved stories → off → Retry. Mention seven-day expiry, failed-feed handling, and the tests.

**6:30 Wrap-up (15 s).** One limitation (grouping can split an event; AI uses excerpts) and what was verified.

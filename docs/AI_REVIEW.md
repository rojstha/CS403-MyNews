# Manual review of AI summaries

The PDF requires checking three generated summaries against their inputs and reporting unsupported claims, missing context, and corrections. Do this yourself; the point is human verification.

## Procedure

1. Pick three stories with `summary.status == "ready"` and at least two publishers, ideally including one with perspectives and one marked "Insufficient evidence for distinct perspectives".
2. Save the stored output: `curl https://YOUR-API/stories/STORY_ID > review_N.json`.
3. Inputs are the `articles` in that same JSON (title + excerpt, numbered in the app as [1], [2], … oldest first). Open each original article too, to note context the excerpts lack.
4. Go sentence by sentence through the overview, agreement, disagreement, uncertainty and each perspective claim. For each one, find the excerpt that supports it.
5. Record findings below. A claim is **unsupported** if no input excerpt states it, even if it is true.
6. Fixes: if a pattern of errors comes from the prompt, edit `backend/prompts/summary_system.md`, bump `PROMPT_VERSION` in `backend/app/ai/summarize.py` (this changes every fingerprint, so the next run regenerates), redeploy, run `/admin/collect`, and re-check. Record before/after.

## Worksheet (copy once per summary)

**Story:** … **Story ID:** … **Summary version / generated_at / model:** …
**Inputs:** [1] Publisher – headline · [2] …

| AI statement (quote) | Cited | Supported by input? (which) | Problem type | Correction |
|---|---|---|---|---|
| | | yes / partly / no | unsupported · wrong attribution · overstated certainty · missing context · none | |

- Perspectives: are both viewpoints actually held by people in the articles (not assigned by publisher)? Y/N, notes:
- Missing context the original articles contain but the excerpts do not:
- Verdict: acceptable / needs prompt fix / fixed in prompt vN

## Reviews

1. _pending_
2. _pending_
3. _pending_

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

Draft prepared with Claude Code on 2026-10-27 from the public API (`https://mynews-api-mq6m.onrender.com`), model `granite4.2:3b` via Ollama, prompt v2, input = feed excerpts. **Verify each line yourself against the original articles before submitting.**

Run evidence: AI worker run #2 (trigger `ai`) generated 10 summaries, 0 failed, 365 s. All 10 passed the automated citation check (every cited ID is an article in that story).

### 1. "Trump administration charges former FBI Director James Comey for the third time" (PBS, NPR, CBS ×2)

| AI statement | Cited | Supported? | Problem | Correction |
|---|---|---|---|---|
| Administration is attempting a third prosecution for alleged disclosure of classified information | 1–4 | yes (1, 2, 3) | none | |
| Comey's lawyers dismissed the effort as invalid and outside the time limit | 2 | yes (NPR) | none | |
| Perspective "Trump administration": prosecuting for "what it calls" disclosing classified information | 1, 2 | yes | none | |
| Perspective "Comey's legal team": invalid, outside time limit; Comey "still innocent" | 2, 4 | yes (NPR excerpt; CBS headline) | none | |

Verdict: **acceptable.** Missing context: excerpts do not explain the grand-jury bypass or the earlier two cases.

### 2. "Jordan attacks militants in Syria in retaliation for church attack" (Guardian, BBC, Al Jazeera)

| AI statement | Cited | Supported? | Problem | Correction |
|---|---|---|---|---|
| Jordan carried out airstrikes in retaliation for a church attack that killed nine | 1 | yes (Guardian) | none | |
| "Articles differ on the number of victims (nine in Guardian, five in BBC)" | n/a | **no** | unsupported: nine died in the church attack, five in the strike; different events | No disagreement on casualty counts |
| Uncertain "whether the strike was carried out by Jordanian forces or Syrian authorities" | n/a | **no** | invented uncertainty: all three say Jordan struck | Remove |
| Perspectives: Jordanian air force / Syrian health officials / victims' families deny links | 1 / 2 / 3 | yes | none | |

Verdict: **perspectives good; two unsupported claims in disagreement/uncertainty.**

### 3. "Local ceasefire brokered by Melania Trump starts in southern Ukraine" (NPR, Al Jazeera)

| AI statement | Cited | Supported? | Problem | Correction |
|---|---|---|---|---|
| Localized ceasefire took effect ahead of a humanitarian mission brokered by Melania Trump | 1 | yes (NPR) | none | |
| Agreement: both sources say it was brokered by Melania Trump | n/a | **partly** | overstated: Al Jazeera reports competing claims (Vatican) | "NPR credits Melania Trump; Al Jazeera reports competing claims" |
| Perspective "Supporters: argue it is beneficial and should be maintained" | 1 | **no** | invented viewpoint | Remove |
| Perspective "Critics: argue it is insufficient or improperly brokered" | 2 | **no** | invented; actual contrast is White House vs Vatican over credit | "White House: Melania Trump brokered it" vs "Vatican: the pope's role" |

Verdict: **fails the "do not invent opposition" rule.**

### Attempted fix and result

A prompt v3 (named groups only, no generic Supporters/Critics, check that numbers describe the same event) was tested read-only on these three stories. It removed the invented ceasefire viewpoints but named a publisher ("Al Jazeera") as a perspective, lost the valid Comey perspectives, and kept the casualty-count error. v3 was **not adopted**; production stays on v2. Conclusion: these errors are limits of the free 3B model on 8 GB RAM. They are disclosed in the app (AI-generated label, citations, input-scope note) and in the README limitations. A larger free model (e.g. qwen3.5:4b, 3.3 GB) could be evaluated the same way.

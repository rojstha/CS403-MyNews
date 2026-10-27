# AI development reflection (draft: edit into your own words)

> Sections marked ✏️ must be written by you; only you know what you checked and how you used ChatGPT.

## Tools used

- **Claude Code** (Claude Opus 5.5, VS Code extension): inspected the starter and assignment, wrote the FastAPI backend, grouping, Wikipedia lookup, AI summarisation pipeline, Flutter app, tests and documentation, and ran the tests and a live collection.
- **ChatGPT** ✏️: describe what you used it for (e.g. explaining concepts, reviewing a plan, debugging a specific error).
- **Anthropic Claude API** (`claude-opus-5-5`) is also *part of the product*: the backend uses it to write story analyses.

## Two representative prompts

1. To Claude Code (opening prompt, abridged): *"Act as my senior Flutter and backend developer and coding tutor… Read the PDF and inspect every starter file BEFORE modifying code… Do not claim a test, deployment, AI call, or phone demo succeeded unless verified… Keep a checklist of completed, unverified, and blocked requirements."*
2. ✏️ A second prompt you actually used, e.g. to ChatGPT or a follow-up to Claude Code.

## An AI-generated mistake that was found and corrected

The first version of the story-grouping algorithm (AI-written) merged two different events: the Justice Department's third prosecution of James Comey and a judge's ruling that his daughter was illegally fired. Both mention "James Comey", "Justice Department" and "FBI", and with a similarity threshold of 0.30 and single-link matching (one similar article was enough) they became one story. That breaks the assignment rule that one shared person is not enough. It was caught by an automated test built from a labelled fixture of real headlines. The fix raised the pair threshold to 0.35, added a rule that a new article must also be similar to the story as a whole (preventing chaining), and smoothed the word-rarity (IDF) weights so small batches behave like large ones. The fix was then checked against a live collection of 283 articles, where the two Comey stories stayed separate and 18 multi-publisher groups showed no wrong merges.

Other AI mistakes found in testing are listed in the defect log (`docs/RELEASE.md`): a Wikipedia User-Agent that Wikimedia blocks (403), and two layout overflows at large text sizes.

## What I personally verified ✏️

Suggested items. Keep only what you actually did:
- Read the grouping code and can explain each rule; checked the live multi-publisher groups for wrong merges.
- Opened publisher and background buttons on the phone and confirmed they match the story.
- Compared three AI summaries against their input excerpts (`docs/AI_REVIEW.md`).
- Watched `/status` show consecutive scheduled runs; confirmed no secrets in the repository or APK.
- Ran the three core-workflow regression passes on the phone.

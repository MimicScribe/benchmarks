# Transform Benchmark

Evaluates Transform mode in [MimicScribe](https://mimicscribe.app) — select text, hold the hotkey, speak an instruction, and the AI edits the selection in place. Because the feature touches text the user already cares about, every edit is high-stakes: a silently reformatted number, a dropped year on a date, or a "canonical" fact from a Reference Doc overwriting the user's own wording is a real bug that erodes trust.

38 scenarios are run 3 times each at two temperatures (0.1 and 1.0) against the production prompt. Each run is scored by deterministic assertions; scenarios where voice / tone / semantic correctness can't be regex-checked also carry a Claude Sonnet judge rubric.

## Models

| Call | Model | Thinking | Purpose |
|------|-------|----------|---------|
| Transform | Gemini 3 Flash | minimal | Text transformation |
| Judge | Claude Sonnet | — | LLM-as-judge for voice, tone, and semantic rubrics |

## What's Tested

### Number, date, and URL preservation

Transform is expected to preserve the **precision and meaning** of numeric values: no rounding, no dropped digits or years, no new numbers derived by calculation, no "$1.23M" compression of "$1,234,567.89". Surface-format changes (`$40,000` ↔ `$40k`, ISO ↔ written dates) are allowed only when the value is preserved and the instruction invites them.

Scenarios cover: phone numbers across format variants, version strings including pre-release tags, complex URLs with query parameters and fragments, large figures with comma separators and cents, percentages to precision, and date formats.

### Anti-injection (context doesn't bleed into unrelated output)

Your Context, Reference Documents, Writing Samples, and Vocabulary are treated as background, not as content sources. Scenarios test that these don't leak into outputs when the user's instruction and selection are about something else entirely: personal messages, casual content, work outside the referenced domain.

### Keyword-collision resilience

Scenarios engineered to tempt the model into pulling reference material via surface-level pattern matches — words, names, dates, prices, or domain terms that appear in both the selection and the Reference Docs but refer to different things (e.g., a common first name shared between a friend and a Reference Doc contact).

### Selection wins over reference

When the selected text states a fact that contradicts Reference Documents or Your Context, the selection's version is kept verbatim. Silent "corrections" against canonical sources are forbidden — the user's wording is authoritative.

### Preservation of structural content

Text inside quotation marks, parentheses, and code blocks is treated as another author's content and copied verbatim, regardless of the instruction. Scenarios also test Markdown structure preservation, email sign-off preservation, and email addresses / URLs appearing as literal strings.

### Voice matching from writing samples

When the user has provided writing samples, Transform applies that voice to rewrites. Scenarios verify that the voice lifts (e.g., stripping hedging, dropping corporate filler) and that an explicit tone instruction beats the writing samples when they conflict.

### Precise-target edits

Instructions that name a specific region ("rename the variable `count` to `total`", "capitalize the first letter of each sentence") must touch only the named region and leave the rest of the selection byte-identical.

### Minimal-edit adherence

Vague instructions like "clean this up" or "make it better" must trigger the smallest defensible edit — up to and including zero edits when the selected text is already clean. Scenarios also include an idempotent case (removing a feature that doesn't exist in the input) and a polished-input case (already-clean prose with a soft instruction).

### Non-English handling

Scenarios test that input in another language (e.g., Spanish) produces output in that language and that English reference content doesn't bleed in.

### Explicit-instruction override

When the spoken instruction contradicts a style guide loaded via Reference Documents (e.g., a forbidden-word list), the user's instruction wins.

## Methodology

- **Two temperatures** per run — 0.1 for near-deterministic production-like behavior, 1.0 for sampling stress. A rule that only holds at low temperature doesn't bite under real-world sampling noise.
- **Three runs per case per temperature** — reveals jitter and cross-run consistency. Every failure mode reported in the results stays across multiple runs, not a single unlucky draw.
- **Corpus grows; cases are never removed.** When users find a new failure mode in the wild, a scenario is added. New prompt iterations must beat the current baseline without regression on any existing case.
- **Test-correctness discipline.** When a case appears to fail but the output is actually correct (e.g., regex was too strict), the test is fixed — not the case. Every fix is documented in the case comments.
- **Prompt mirror.** The benchmark runner mirrors the production Swift prompt byte-for-byte. When the app's prompt changes, the benchmark changes in the same commit.

## Prompt-validation discipline

Transform's system prompt stays short by design — every bullet and every preamble rule must justify itself. Changes to the prompt are A/B-tested against the corpus before landing. Additions that don't measurably improve pass rates are dropped, even when they "feel right." The prompt today is roughly 175 words across 8 bullets, with a further ~80-word preamble-guardrail block emitted only when context blocks are present.

## Known limitations

A few failure modes where the model doesn't yet reliably hold the line, tracked for future prompt iterations:

- **"Clean this up" on already-polished prose** — the model sometimes restructures well-formed text, dropping articles or abbreviating phrases. Workaround: use a more specific instruction ("fix typos") rather than a broad cleanup request.
- **Year-dropping on dates under "make polished"** — when a year appears twice in quick succession, the model occasionally drops the second one. The prompt explicitly forbids this; the model weighs conciseness slightly higher.
- **Rare reference leakage on extremely vague "add detail"** — on generic selections, the model occasionally pulls specifics from Reference Documents. Mostly fixed by preamble consolidation but still surfaces at high temperatures.

## Results

See [results/RESULTS.md](results/RESULTS.md) for current pass rates and latency.

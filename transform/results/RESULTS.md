# Transform Benchmark Results

Pipeline: Gemini 3 Flash (transform) + Claude Sonnet (judge on applicable cases)

Run date: 2026-04-20 | 38 scenarios | 3 runs each × 2 temperatures (0.1 and 1.0)

## Summary

| Metric | Value |
|--------|-------|
| Full pass rate — temp 0.1 | **93.9%** |
| Full pass rate — temp 1.0 | **93.9%** |
| Deterministic-assertion pass rate | 94% |
| Judge pass rate (applicable cases) | 96% |
| Average latency | **2.8s** (temp 1.0) / **3.2s** (temp 0.1) |
| Total runs | 228 (114 per temperature) |
| Network errors | 1 of 228 |

At production temperature (1.0), 71 of 76 scenario-runs fully passed every deterministic assertion AND every applicable judge rubric. Same result at temp 0.1 — stability across temperatures is a deliberate goal; a prompt rule that only holds at low temperature doesn't bite under real sampling noise.

## Pass rate by category

| Category | Pass rate | Scenarios |
|----------|-----------|-----------|
| Number, date, and URL preservation | 100% | 6 |
| Keyword-collision resilience | 100% | 5 |
| Code identifier rename | 100% | 1 |
| Voice matching from writing samples | 100% | 3 |
| Baseline edits (no context dependency) | 100% | 2 |
| Explicit-instruction override | 100% | 2 |
| Precise-target edits | 100% | 2 |
| Non-English handling | 100% | 1 |
| Negation honoring | 100% | 1 |
| Idempotent no-op | 100% | 1 |
| Anti-injection from Reference Docs | 92% | 13 |
| Context-trap resilience | 88% | 8 |
| Preservation (quotes, markdown, email sign-offs) | 94% | 18 |
| Selection-wins-over-reference | 83% | 1 |
| Minimal-edit adherence | 80% | 5 |
| Vague-instruction restraint | 67% | 2 |

Categories scoring 100% held across both temperatures and all 6 runs per scenario. Categories below 100% are documented in [Known failure modes](#known-failure-modes).

## Prompt-validation history

Transform's prompt has gone through seven iterations against this corpus. The principle: every addition must measurably improve pass rates or it's dropped to save tokens and latency.

| Iteration | Change | Result | Decision |
|-----------|--------|--------|----------|
| v1 | Initial prompt (7 bullets) | Baseline measurement | — |
| v2 | Added preamble "context is background" rule | 91% / 92% | Kept |
| v3 | Added explicit vague-instruction rule + quote-preservation bullet | 86% / 89% (-5pp) | Kept bullet, vague rule weak |
| v4 | Consolidated preamble into 3-item block, dropped "Tailor responses" line (was encouraging context injection) | 90% / 90% | Kept — dropping the line fixed vague-instruction leakage |
| v5 | Reworded quote-preservation rule, added zero-edits carve-out for vague instructions, fixed test bugs | 94% / 93% | Kept — quote preservation + target-region tests now clean |
| v6 | Added number / date / URL preservation rule (too strict: forbade format changes) | 95% / 94% | Kept but rule needed refinement |
| v7 | Refined number rule from "preserve verbatim format" to "preserve precision and meaning" — format changes OK when value stays intact | **94% / 94%** | **Current production** |

### Changes that were tried and dropped

- **"For vague instructions, treat ambiguity as license to import named entities from context"** (hypothetical stronger vague rule) — tested phrasings with this framing regressed RAG-helpful cases, where the instruction *does* legitimately ask for named content. Dropped.
- **A separate "Tailor responses to the user's role and expertise" line** — this was in the original preamble and was found to actively encourage context injection. Removing it fixed 3/3 vague-instruction leakage cases. Not reinstated.
- **Instructing the model to "return input unchanged when already clean"** — considered for the polished-input regression, but would require aggressive phrasing that risks suppressing legitimate edits elsewhere. Not worth the prompt bloat.

## Where we've measurably improved

Comparing v1 (initial) to v7 (current) on specific failure modes that v1 failed:

- **Silent fact overwrite** — user writes `$60,000` and the selection contradicts a Reference Doc that says `$48k`. v1: the model rewrote to `$48k` 6/6 times. v7: keeps `$60k` 5/6 times. The remaining leakage is a tier-name carryover (`Starter is $60k/year`), not a price change.
- **Vague-instruction invention** — user selects a generic sentence about a meeting going well and says "add detail" with Reference Docs loaded. v1: pulled specific project names / prices / dates from Reference Docs 6/6 times. v7: behaves correctly most runs; occasional leakage at temp 1.0.
- **Number mangling** — on large figures like `$1,234,567.89`, v1 would compress to `$1.23M` (losing cents + 3 significant figures) and occasionally invent derived percentages. v7: every run preserves the full figure.
- **Context-trap collisions** — on personal content (birthday presents, dentist appointments, kids' school activities) with unrelated work Reference Docs loaded, v1 sometimes dragged in work context via word-level collisions. v7: 30/30 runs across all collision scenarios stay on topic.

## Known failure modes

Tracked for future prompt iterations. Each is documented in the corpus with the actual failing output so regressions surface immediately if a future change re-introduces them.

### "Clean this up" on already-polished prose (0 of 6 runs)

The zero-edits carve-out ("up to and including zero edits when the text is already clean") in the prompt doesn't override "clean this up" when the model perceives room for tightening. The model abbreviates `year-over-year` → `YoY`, drops articles, splits compound sentences. Fix would require a stronger "return input unchanged when no errors exist" rule, which risks suppressing legitimate edits elsewhere.

### Year-dropping on polish (1-3 of 6 runs)

When a year appears twice in close succession and the instruction is "make this polished", the model occasionally drops the second occurrence. The prompt rule "Preserve numeric precision and meaning — don't round, drop digits or years, or derive new numbers" doesn't reliably bite against "polish = concise" weighing.

### Vague-instruction jitter on generic selections (1 of 3 runs at each temperature)

Mostly fixed by the v4 preamble consolidation (6/6 → ~5/6). Occasional leakage of named entities into outputs when the selection is generic and the instruction is minimal ("add detail"). Does not affect non-vague instructions.

## Latency

| Temperature | Average | Median | p95 |
|-------------|---------|--------|-----|
| 0.1 | 3.2s | 3.1s | 5.5s |
| 1.0 | 2.8s | 2.7s | 5.2s |

Latency is dominated by the Gemini Flash response. Preamble construction, prompt assembly, and keystroke replay are all sub-10ms. The reference-context retrieval pass (embedding + similarity search) adds ~100ms when Reference Documents are configured, less when the index is empty.

## Adding a failure mode

If you find behavior in Transform that seems wrong, open an issue with:
- The exact selected text
- The spoken instruction
- The observed output
- What you expected instead

Confirmed failure modes are added to the corpus as regression cases. The principle is additive: cases are never removed, only fixed.

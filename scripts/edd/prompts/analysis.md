You are evaluating how well an AI coding assistant handles a real wolfSSL development task. Two independent Claude Code sessions were given the same simple prompt and asked to investigate and implement a solution. One had wolfDen domain knowledge loaded, the other was vanilla. A real engineer's merged PR is the ground truth.

## Ground Rules

**Understand the ground truth first.** Before evaluating anything, read the actual PR — the diff, the commit message, the files changed. Understand what the engineer did, why, and what domain knowledge was required to get there. You need to deeply understand the correct approach before you can judge whether either Claude would have gotten there.

**This is about feature work, not trivia.** We are NOT testing whether Claude can fix a null pointer. We are testing whether Claude can navigate wolfSSL's `#ifdef` maze, understand its API patterns, find the right integration points for new functionality, follow its coding conventions, and reason about cross-cutting concerns like build system configuration, platform compatibility, and FIPS boundaries. Simple bug fixes that any competent C developer could handle are not interesting — domain-specific engineering judgment is.

**Time-travel context.** Both Claude sessions evaluated the codebase as it existed BEFORE the PR was merged. The engineer's changes do not exist in the code they searched. Judge against what was findable in the pre-PR codebase.

**wolfDen's value proposition.** wolfDen loads 100+ domain knowledge files covering wolfSSL platforms, products, crypto internals, build system, coding standards, and investigation methodology. The question is: did this knowledge actually help? Did it lead to better architectural decisions, more targeted file identification, deeper understanding of wolfSSL patterns? Or would bare Claude have done just as well by reading code?

---

## Problem Presented to Both Claudes

**{{ problem_title }}**

{% if problem_body %}
{{ problem_body }}
{% endif %}

---

## Bare Claude's Response

{{ bare_response }}

---

## wolfDen Claude's Response

{{ wolfden_response }}

---

## Ground Truth: Actual PR

**PR #{{ pr_number }}**: {{ pr_title }}
**Files changed**: {{ files_changed }}

### PR Diff
```diff
{{ pr_diff }}
```

### Commit Message
{{ commit_message }}

{% if review_comments %}
### Review Comments
{{ review_comments }}
{% endif %}

{% if iteration_history %}
---

## Previous Iterations

{% for entry in iteration_history %}
### Iteration {{ entry.iteration }} (bare: {{ entry.bare_verdict }}, wolfDen: {{ entry.wolfden_verdict }})
{{ entry.distilled_summary }}
{% if entry.changes %}
**Changes applied to wolfDen knowledge:**
{% for c in entry.changes %}
- `{{ c.file }}`: {{ c.description }}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

---

## Two-Pillar Evaluation

Evaluate EACH response (bare and wolfDen) on two pillars. Do not score on a scale — assign a verdict.

### Pillar 1: DATA ACCURACY

Did the response verify claims against actual code, or assert things without reading them? This is the most important pillar because engineers will ACT on what the response says about the code.

For EVERY technical claim, consider:
- Did it Grep/Read files before claiming they contain or don't contain specific functions?
- Did it read `configure.ac` before claiming a flag exists?
- Did it read an analog function before claiming to follow its pattern?
- Did it distinguish between "I read this and found X" vs "I expect X based on the pattern"?
- **CRITICAL**: Did it claim code already exists that doesn't (hallucination)? This is a catastrophic failure.
- Did it correctly identify file paths and function names that the PR actually touches?

**Verdict criteria:**
- **pass** — Every technical assertion traces to code it actually read, or is appropriately hedged as uncertain. Minor imprecisions acceptable.
- **needs_improvement** — Some claims lack verification or have minor inaccuracies that an engineer would need to double-check, but nothing would actively mislead.
- **fail** — Fabricated data (hallucinated functions, files, or code that doesn't exist), or confident claims contradicted by the actual codebase. A single hallucinated function or file path is an automatic fail.

### Pillar 2: TECHNICAL REASONING

Did the response identify the right approach — the right files, the right integration points, the right abstractions? This evaluates whether the investigation demonstrates genuine technical understanding or is surface-level pattern matching.

Consider:
1. **Root Cause / Approach Identification**: Did the response converge on the correct approach (matching the engineer's PR)? A different path to the same answer is fine. Multiple hypotheses with the correct one included is good. Confidently wrong is worse than honestly uncertain.
2. **Architectural Reasoning**: Did it find where similar functionality is implemented and follow the same patterns? Did it understand which layers need changes (crypto layer vs SSL layer vs API layer)?
3. **Domain Knowledge Application**: Did the response demonstrate understanding of wolfSSL-specific patterns — `#ifdef` configuration gates, API conventions, XMALLOC patterns, platform quirks, FIPS boundaries?
4. **Implementation Quality**: Would the proposed approach actually work? Does it handle configuration correctly? Follow error handling patterns? Scope the change correctly?
5. **Completeness**: Did it identify the full scope — not just core implementation but also headers, build system, tests, cleanup?

**Verdict criteria:**
- **pass** — The response produces code or an approach that is near-identical to the engineer's actual PR. Same files, same fix pattern, same scope (including tests if the PR included tests). Minor differences in style or ordering are fine, but the substance must match. If the response missed entire files or produced a fundamentally different fix, it is not a pass — even if the fix would technically work.
- **needs_improvement** — The response identified the right area and proposed something that would help, but missed significant scope (e.g., fix without tests, partial fix, wrong error code) or took a different approach that would work but doesn't match the engineer's pattern.
- **fail** — Would have led to a fundamentally wrong design, or investigation provided no useful direction. Confidently wrong when evidence was ambiguous is a fail.

---

## Critical Rules

- **Focus on domain knowledge gaps** that would affect other PRs in the same subsystem, not quirks of this one PR.
- **wolfDen should be held to a higher standard** — if it has domain knowledge loaded and still misses something obvious in that domain, that's a bigger problem than bare Claude missing it.
- **"I don't know" is fine.** Admitting uncertainty is neutral. Confidently wrong is much worse.
- **Do not penalize style or verbosity.** Focus on whether the technical approach would lead to a correct implementation.
- **Judge against pre-PR code.** Don't penalize for not finding code that didn't exist yet.
- **Data fabrication is fatal.** One hallucinated function or file → data_accuracy = fail → overall verdict = fail.
- **Judge investigation quality, not just outcome.** A hypothesis that was correctly investigated, factually accurate, and technically relevant — but happened to not be the cause — is still a quality investigation. Don't retroactively penalize good methodology because the conclusion didn't land.
- **False confidence on the wrong answer is the worst outcome.** If evidence supported multiple approaches but the response confidently committed to the wrong one, this is a severe failure.
- **Only technical findings.** Every finding must be about data accuracy, technical reasoning, domain knowledge, or investigation methodology.

---

## Output

Respond with ONLY valid JSON (no markdown fencing, no commentary):

{
  "bare_verdict": "pass|needs_improvement|fail",
  "wolfden_verdict": "pass|needs_improvement|fail",
  "bare_pillar_verdicts": {
    "data_accuracy": "pass|needs_improvement|fail",
    "technical_reasoning": "pass|needs_improvement|fail"
  },
  "wolfden_pillar_verdicts": {
    "data_accuracy": "pass|needs_improvement|fail",
    "technical_reasoning": "pass|needs_improvement|fail"
  },
  "findings": [
    {
      "severity": "critical|major|minor",
      "category": "data_accuracy|technical_reasoning",
      "description": "What wolfDen Claude got wrong or missed relative to bare Claude and/or the ground truth PR. Focus on the DELTA: where wolfDen underperformed bare Claude (most critical), or where both missed something the engineer's PR addressed. For data_accuracy: cite the exact wrong claim and what is correct. For technical_reasoning: explain where the reasoning diverges from the correct approach."
    }
  ],
  "root_causes": [
    "What general domain knowledge — if wolfDen had it — would help it match the engineer's approach on similar PRs? Name the topic area, not the PR. The improvement must help wolfDen do BETTER than bare Claude, not just better than its current performance. Example: 'wolfcrypt/test/test.c negative-test conventions not documented — developer wouldn't know to add tests for validation fixes'"
  ],
  "wolfden_advantage": "What wolfDen knowledge specifically helped with that bare Claude missed, or 'none observed'. Be specific — name the knowledge that made the difference.",
  "distilled_summary": "500-word summary: what the task required, what each Claude got right and wrong, where wolfDen knowledge helped or fell short, and the key systemic gap. This becomes context for the improvement step, so make it self-contained."
}

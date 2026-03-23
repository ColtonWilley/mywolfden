from __future__ import annotations

"""Three-way analysis: bare vs wolfDen vs engineer's actual PR.

Uses claude -p to compare both eval responses against the PR ground truth
using two-pillar qualitative evaluation (data accuracy + technical reasoning).
All analysis uses Opus for maximum reasoning quality.
"""

import logging

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import PROMPTS_DIR
from .llm import call_claude_json

logger = logging.getLogger(__name__)

_jinja_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)

_VALID_VERDICTS = {"pass", "needs_improvement", "fail"}
_VERDICT_RANK = {"fail": 0, "needs_improvement": 1, "pass": 2}
_VERDICT_TO_SCORE = {"pass": 0.85, "needs_improvement": 0.55, "fail": 0.25}

# Max chars for PR diff in analysis prompt
_MAX_DIFF_CHARS = 15000


def _validate_verdict(verdict: str | None, fallback: str = "needs_improvement") -> str:
    """Ensure verdict is one of the valid values."""
    if verdict and verdict.lower() in _VALID_VERDICTS:
        return verdict.lower()
    return fallback


def _compute_overall_verdict(pillar_verdicts: dict) -> str:
    """Derive overall verdict from pillar verdicts.

    - If either pillar is "fail" -> "fail"
    - If both are "pass" -> "pass"
    - Otherwise -> "needs_improvement"
    """
    da = pillar_verdicts.get("data_accuracy", "needs_improvement")
    tr = pillar_verdicts.get("technical_reasoning", "needs_improvement")
    if da == "fail" or tr == "fail":
        return "fail"
    if da == "pass" and tr == "pass":
        return "pass"
    return "needs_improvement"


def verdict_to_synthetic_composite(verdict: str) -> float:
    """Map a verdict to a synthetic composite score for backward compatibility."""
    return _VERDICT_TO_SCORE.get(verdict, 0.55)


def _build_iteration_history(
    analysis_history: list[dict],
    improvements: list[dict],
) -> list[dict]:
    """Build iteration history entries."""
    history = []
    for entry in analysis_history:
        iteration = entry["iteration"]
        changes = [i for i in improvements if i.get("iteration") == iteration]
        history.append({
            "iteration": iteration,
            "bare_verdict": entry.get("bare_verdict", entry.get("bare_score", "?")),
            "wolfden_verdict": entry.get("wolfden_verdict", entry.get("wolfden_score", "?")),
            "distilled_summary": entry.get("distilled_summary", ""),
            "changes": changes,
        })
    return history


def analyze(
    bare_response: str,
    wolfden_response: str,
    pr_data: dict,
    pr_diff: str,
    problem_desc: dict,
    iteration: int,
    analysis_history: list[dict],
    improvements: list[dict],
    model: str = "opus",
) -> dict:
    """Run three-way analysis comparing bare, wolfden, and engineer.

    Args:
        bare_response: Bare Claude's investigation response
        wolfden_response: wolfDen Claude's investigation response
        pr_data: PR metadata (number, title, body, files, mergeCommit, etc.)
        pr_diff: The PR diff text
        problem_desc: {title, body} of the problem presented
        iteration: Current iteration number (0 = baseline)
        analysis_history: Previous analyses
        improvements: All improvements applied
        model: Claude model for analysis

    Returns:
        Analysis dict with verdicts, findings, root_causes, etc.
    """
    template = _jinja_env.get_template("analysis.md")

    # Truncate diff if too large
    diff_text = pr_diff
    if len(diff_text) > _MAX_DIFF_CHARS:
        diff_text = diff_text[:_MAX_DIFF_CHARS] + f"\n... [truncated, {len(pr_diff)} chars total]"

    # File list
    files = pr_data.get("files", [])
    files_changed = ", ".join(f.get("path", "?") for f in files[:20])
    if len(files) > 20:
        files_changed += f" ... and {len(files) - 20} more"

    # Commit message: use PR body if available, else title
    commit_message = pr_data.get("body", "") or pr_data.get("title", "")
    if len(commit_message) > 2000:
        commit_message = commit_message[:2000] + "\n... [truncated]"

    # Review comments if available from PR data
    reviews = pr_data.get("reviews", []) or []
    review_comments = ""
    if reviews:
        review_lines = []
        for r in reviews[:5]:
            author = r.get("author", {}).get("login", "?") if isinstance(r.get("author"), dict) else "?"
            body = r.get("body", "") or ""
            if body.strip():
                review_lines.append(f"**{author}**: {body[:500]}")
        review_comments = "\n\n".join(review_lines)

    # Build iteration history for context
    iteration_history = _build_iteration_history(analysis_history, improvements)

    rendered = template.render(
        problem_title=problem_desc.get("title", "Unknown"),
        problem_body=problem_desc.get("body", ""),
        bare_response=bare_response,
        wolfden_response=wolfden_response,
        pr_number=pr_data.get("number", 0),
        pr_title=pr_data.get("title", ""),
        files_changed=files_changed,
        pr_diff=diff_text,
        commit_message=commit_message,
        review_comments=review_comments,
        iteration_history=iteration_history if iteration_history else None,
    )

    logger.info("Running three-way analysis (iteration %d, model=%s)...", iteration, model)
    analysis = call_claude_json(rendered, model=model)

    # Validate and normalize verdicts
    bare_pillars = analysis.get("bare_pillar_verdicts", {})
    wolfden_pillars = analysis.get("wolfden_pillar_verdicts", {})

    bare_pillars["data_accuracy"] = _validate_verdict(bare_pillars.get("data_accuracy"))
    bare_pillars["technical_reasoning"] = _validate_verdict(bare_pillars.get("technical_reasoning"))
    wolfden_pillars["data_accuracy"] = _validate_verdict(wolfden_pillars.get("data_accuracy"))
    wolfden_pillars["technical_reasoning"] = _validate_verdict(wolfden_pillars.get("technical_reasoning"))

    analysis["bare_pillar_verdicts"] = bare_pillars
    analysis["wolfden_pillar_verdicts"] = wolfden_pillars

    # Compute overall verdicts from pillars
    analysis["bare_verdict"] = _compute_overall_verdict(bare_pillars)
    analysis["wolfden_verdict"] = _compute_overall_verdict(wolfden_pillars)

    # Synthetic composites for backward compatibility
    analysis["bare_composite"] = verdict_to_synthetic_composite(analysis["bare_verdict"])
    analysis["wolfden_composite"] = verdict_to_synthetic_composite(analysis["wolfden_verdict"])

    logger.info(
        "Analysis complete: bare=%s, wolfden=%s",
        analysis["bare_verdict"], analysis["wolfden_verdict"],
    )

    return analysis

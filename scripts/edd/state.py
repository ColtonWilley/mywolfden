from __future__ import annotations

"""State file management for the wolfDen EDD loop.

Single-track PR-based workflow. Atomic writes via temp file + rename.
Verdict-based: stores pass/needs_improvement/fail instead of numeric scores.
Backward-compatible with old score-based state files.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import STATE_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _empty_pr(pr_number: int, repo: str) -> dict:
    return {
        "pr_number": pr_number,
        "repo": repo,
        "iteration": 0,
        "bare_result": None,
        "wolfden_results": [],      # [baseline, iter1, iter2, ...]
        "improvements": [],
        "analysis_history": [],     # [{iteration, bare_verdict, wolfden_verdict, ...}]
    }


def _empty_state(iterations: int = 2) -> dict:
    return {
        "status": "idle",
        "updated_at": _now_iso(),
        "iterations_per_pr": iterations,
        "candidate_queue": [],      # [{pr_number, repo}, ...]
        "current_pr": None,
        "completed_prs": [],
        "error_log": [],
    }


def load_state() -> dict:
    """Load state from disk. Returns empty state if file doesn't exist.

    Falls back to .bak file on corrupt JSON.
    """
    path = Path(STATE_FILE)
    if not path.exists():
        return _empty_state()
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        bak = Path(str(path) + ".bak")
        if bak.exists():
            logging.getLogger(__name__).warning(
                "State file corrupt, loading from backup"
            )
            return json.loads(bak.read_text())
        raise


def save_state(state: dict) -> None:
    """Atomic write: write to .tmp then rename."""
    state["updated_at"] = _now_iso()
    path = Path(STATE_FILE)

    if path.exists():
        shutil.copy2(path, str(path) + ".bak")

    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    os.rename(tmp, str(path))


def get_resume_step(state: dict) -> str | None:
    """Determine where to resume for the current PR.

    Returns one of: 'bare', 'wolfden_baseline', 'analyze_baseline',
    'improve', 'reeval', 'analyze_iter', 'report', or None.
    """
    pr = state.get("current_pr")
    if not pr:
        return None

    iteration = pr.get("iteration", 0)
    bare_result = pr.get("bare_result")
    wolfden_results = pr.get("wolfden_results", [])
    improvements = pr.get("improvements", [])
    analysis_history = pr.get("analysis_history", [])

    # No bare eval yet
    if bare_result is None:
        return "bare"

    # No wolfden baseline yet
    if not wolfden_results:
        return "wolfden_baseline"

    # Baseline exists but no analysis yet
    if not analysis_history:
        return "analyze_baseline"

    # Check current iteration state
    n_wolfden = len(wolfden_results)  # includes baseline
    n_analyses = len(analysis_history)
    iter_improvements = [i for i in improvements if i.get("iteration") == iteration]

    # Check if we have a re-eval result for this iteration
    if n_wolfden > iteration + 1:
        # We have the re-eval result; check if analyzed
        if n_analyses <= iteration + 1:
            return "analyze_iter"
        return "report"

    # No re-eval yet for this iteration
    if iter_improvements:
        # Improvements applied, need re-eval
        return "reeval"

    # Need to propose improvements
    return "improve"


def record_bare_result(state: dict, result: dict) -> None:
    """Record the bare arm eval result."""
    state["current_pr"]["bare_result"] = result


def record_wolfden_result(state: dict, result: dict) -> None:
    """Record a wolfden arm eval result (baseline or iteration)."""
    state["current_pr"]["wolfden_results"].append(result)


def record_improvement(state: dict, file: str, description: str,
                       iteration: int, action: str = "unknown") -> None:
    """Record an applied improvement."""
    state["current_pr"]["improvements"].append({
        "file": file,
        "description": description,
        "iteration": iteration,
        "action": action,
    })


def record_analysis(state: dict, iteration: int, bare_verdict: str,
                    wolfden_verdict: str, distilled_summary: str) -> None:
    """Record three-way analysis results with verdicts."""
    state["current_pr"]["analysis_history"].append({
        "iteration": iteration,
        "bare_verdict": bare_verdict,
        "wolfden_verdict": wolfden_verdict,
        "distilled_summary": distilled_summary,
    })


def complete_pr(state: dict, verdict: str, bare_verdict: str,
                wolfden_baseline_verdict: str, wolfden_final_verdict: str) -> None:
    """Move current PR to completed, preserving improvements for reports."""
    pr = state["current_pr"]
    state["completed_prs"].append({
        "pr_number": pr["pr_number"],
        "repo": pr["repo"],
        "bare_verdict": bare_verdict,
        "wolfden_baseline_verdict": wolfden_baseline_verdict,
        "wolfden_final_verdict": wolfden_final_verdict,
        "verdict": verdict,
        "improvements": pr.get("improvements", []),
    })
    state["current_pr"] = None


def pop_next_candidate(state: dict) -> dict | None:
    """Pop next candidate from queue into current_pr. Returns {pr_number, repo} or None."""
    queue = state["candidate_queue"]
    if not queue:
        return None
    candidate = queue.pop(0)
    state["current_pr"] = _empty_pr(candidate["pr_number"], candidate["repo"])
    return candidate


def log_error(state: dict, message: str, pr_number: int | None = None) -> None:
    """Append an error to the error log."""
    state["error_log"].append({
        "timestamp": _now_iso(),
        "pr_number": pr_number,
        "message": message,
    })

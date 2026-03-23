from __future__ import annotations

"""wolfDen Eval-Driven Development (EDD) loop.

Two-arm eval: bare Claude vs wolfDen Claude, compared against actual PRs.
Identifies knowledge gaps, proposes improvements to .claude/rules/ files,
re-evaluates to measure impact.

Uses two-pillar qualitative evaluation (data accuracy + technical reasoning)
with verdicts (pass/needs_improvement/fail) instead of numeric scores.

Usage:
    python -m scripts.edd                          # default: 2 iterations
    python -m scripts.edd --pr 9800                # specific PR
    python -m scripts.edd --iterations 1 --review  # proposals for review
    python -m scripts.edd --resume                 # resume from state file
    python -m scripts.edd --dry-run                # show plan without executing
"""

import argparse
import json
import logging
import sys

from . import WOLFDEN_DIR, REPORTS_DIR
from .state import (
    load_state, save_state, get_resume_step,
    record_bare_result, record_wolfden_result,
    record_improvement, record_analysis, complete_pr,
    pop_next_candidate, log_error, _empty_state,
)
from .dispatcher import dispatch_eval, check_server_health, EvalError
from .candidates import (
    fetch_merged_prs, fetch_pr_detail, fetch_pr_diff,
    filter_candidates, select_diverse_candidate,
    extract_problem_description,
)
from .workspace import (
    setup_workspace, teardown_workspace, fetch_origin,
    commit_exists, verify_clean, WorkspaceError,
)
from .analyzer import analyze
from .improver import propose_improvements, apply_proposal, write_proposal_for_review
from .report import generate_pr_report, generate_summary_report

logger = logging.getLogger("edd")

# Verdict rank for improvement detection
_VERDICT_RANK = {"fail": 0, "needs_improvement": 1, "pass": 2}


def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _render_eval_prompt(problem_desc: dict) -> str:
    """Build a simple, realistic developer prompt."""
    title = problem_desc.get("title", "")
    body = problem_desc.get("body", "")

    parts = []
    if title:
        parts.append(title)
    if body:
        parts.append("")
        parts.append(body)
    parts.append("")
    parts.append("Investigate and fix this.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_pr_eval(
    state: dict,
    iterations: int,
    auto_apply: bool,
    model: str,
    eval_model: str,
) -> None:
    """Run the full eval loop for the current PR."""
    pr = state["current_pr"]
    pr_number = pr["pr_number"]
    repo = pr["repo"]

    logger.info("=" * 60)
    logger.info("Evaluating PR #%d (%s)", pr_number, repo)
    logger.info("=" * 60)

    # Fetch PR metadata and diff
    logger.info("Fetching PR data...")
    pr_data = fetch_pr_detail(pr_number, repo=repo)
    pr_diff = fetch_pr_diff(pr_number, repo=repo)
    problem_desc = extract_problem_description(pr_data, repo=repo)
    task_prompt = _render_eval_prompt(problem_desc)

    logger.info("Problem: %s (source: %s)", problem_desc.get("title", "?"), problem_desc.get("source", "?"))

    # Get merge commit for workspace setup
    merge_commit = pr_data.get("mergeCommit", {})
    if isinstance(merge_commit, dict):
        merge_commit = merge_commit.get("oid", "")
    if not merge_commit:
        logger.error("PR #%d has no merge commit", pr_number)
        log_error(state, f"No merge commit for PR #{pr_number}", pr_number)
        save_state(state)
        return

    # Ensure commit exists locally
    if not commit_exists(merge_commit):
        logger.info("Merge commit not found locally, fetching...")
        fetch_origin()
        if not commit_exists(merge_commit):
            logger.error("Merge commit %s not found even after fetch", merge_commit[:12])
            log_error(state, f"Merge commit not found: {merge_commit[:12]}", pr_number)
            save_state(state)
            return

    # Setup workspace (checkout pre-PR state)
    workspace_ctx = None
    try:
        workspace_ctx = setup_workspace(merge_commit)
        step = get_resume_step(state)
        logger.info("Resume step: %s", step)

        # ---- BARE EVAL ----
        if step == "bare":
            logger.info("Dispatching bare eval...")
            bare_result = dispatch_eval(
                task_prompt, mode="bare", model=eval_model,
            )
            record_bare_result(state, bare_result)
            save_state(state)
            step = "wolfden_baseline"

        # ---- WOLFDEN BASELINE ----
        if step == "wolfden_baseline":
            logger.info("Dispatching wolfDen baseline eval...")
            wolfden_result = dispatch_eval(
                task_prompt, mode="wolfden", model=eval_model,
            )
            record_wolfden_result(state, wolfden_result)
            save_state(state)
            step = "analyze_baseline"

        # ---- BASELINE ANALYSIS ----
        baseline_analysis = None
        if step == "analyze_baseline":
            bare_response = pr["bare_result"].get("response", "")
            wolfden_response = pr["wolfden_results"][0].get("response", "")

            logger.info("Running three-way analysis (baseline)...")
            baseline_analysis = analyze(
                bare_response=bare_response,
                wolfden_response=wolfden_response,
                pr_data=pr_data,
                pr_diff=pr_diff,
                problem_desc=problem_desc,
                iteration=0,
                analysis_history=[],
                improvements=[],
                model=model,
            )
            record_analysis(
                state, 0,
                baseline_analysis["bare_verdict"],
                baseline_analysis["wolfden_verdict"],
                baseline_analysis.get("distilled_summary", ""),
            )
            save_state(state)

            logger.info(
                "Baseline — bare: %s, wolfDen: %s",
                baseline_analysis["bare_verdict"],
                baseline_analysis["wolfden_verdict"],
            )
            step = "improve"

        # ---- IMPROVEMENT ITERATIONS ----
        for iter_num in range(1, iterations + 1):
            # Set iteration to match the iteration we're working on.
            # Improvements for iter_num are stored with iteration=iter_num.
            pr["iteration"] = iter_num
            step = get_resume_step(state)

            if step == "report":
                break

            # ---- IMPROVE ----
            if step == "improve":
                # Get findings by re-analyzing (findings aren't persisted in state)
                last_wolfden_response = pr["wolfden_results"][-1].get("response", "")
                re_analysis = analyze(
                    bare_response=pr["bare_result"].get("response", ""),
                    wolfden_response=last_wolfden_response,
                    pr_data=pr_data,
                    pr_diff=pr_diff,
                    problem_desc=problem_desc,
                    iteration=iter_num - 1,
                    analysis_history=pr.get("analysis_history", []),
                    improvements=pr.get("improvements", []),
                    model=model,
                )

                findings = re_analysis.get("findings", [])
                root_causes = re_analysis.get("root_causes", [])

                if findings:
                    logger.info("Proposing improvements (iteration %d)...", iter_num)
                    # Build PR context for the improver
                    pr_context = (
                        f"PR #{pr_number}: {pr_data.get('title', '')}\n"
                        f"Problem: {problem_desc.get('title', '')} "
                        f"({problem_desc.get('source', 'pr')})\n"
                        f"Subsystem: {', '.join(f.get('path', '?').split('/')[0] for f in pr_data.get('files', [])[:5])}\n"
                        f"Summary: {re_analysis.get('distilled_summary', '')[:500]}"
                    )
                    proposals = propose_improvements(
                        findings, root_causes,
                        pr_context=pr_context,
                        wolfden_advantage=re_analysis.get("wolfden_advantage", ""),
                        model=model,
                    )

                    for p in proposals:
                        if auto_apply:
                            success = apply_proposal(p)
                            if success:
                                record_improvement(
                                    state, p["file"],
                                    p.get("reasoning", "")[:200],
                                    iter_num, p.get("action", "unknown"),
                                )
                        else:
                            write_proposal_for_review(p, REPORTS_DIR, pr_number, iter_num)
                else:
                    logger.info("No findings to improve on (iteration %d)", iter_num)

                save_state(state)

                if not auto_apply:
                    logger.info("Review mode — proposals written, stopping iteration loop.")
                    break

                step = "reeval"

            # ---- RE-EVAL (wolfDen only — bare doesn't change) ----
            if step == "reeval":
                logger.info("Dispatching wolfDen re-eval (iteration %d)...", iter_num)
                wolfden_result = dispatch_eval(
                    task_prompt, mode="wolfden", model=eval_model,
                )
                record_wolfden_result(state, wolfden_result)
                save_state(state)
                step = "analyze_iter"

            # ---- ANALYZE ITERATION ----
            if step == "analyze_iter":
                logger.info("Analyzing iteration %d...", iter_num)
                iter_analysis = analyze(
                    bare_response=pr["bare_result"].get("response", ""),
                    wolfden_response=pr["wolfden_results"][-1].get("response", ""),
                    pr_data=pr_data,
                    pr_diff=pr_diff,
                    problem_desc=problem_desc,
                    iteration=iter_num,
                    analysis_history=pr.get("analysis_history", []),
                    improvements=pr.get("improvements", []),
                    model=model,
                )
                record_analysis(
                    state, iter_num,
                    iter_analysis["bare_verdict"],
                    iter_analysis["wolfden_verdict"],
                    iter_analysis.get("distilled_summary", ""),
                )
                save_state(state)

                logger.info(
                    "Iteration %d — wolfDen: %s",
                    iter_num, iter_analysis["wolfden_verdict"],
                )

    except (EvalError, WorkspaceError, RuntimeError) as e:
        logger.error("Error for PR #%d: %s", pr_number, e)
        log_error(state, str(e), pr_number)
        # Record as completed with "failed" verdict so we don't re-select
        history = pr.get("analysis_history", [])
        bare_verdict = history[0].get("bare_verdict", "fail") if history else "fail"
        wolfden_verdict = history[-1].get("wolfden_verdict", "fail") if history else "fail"
        complete_pr(state, "failed", bare_verdict, wolfden_verdict, wolfden_verdict)
        save_state(state)
        return
    finally:
        # Always restore workspace
        if workspace_ctx:
            teardown_workspace(workspace_ctx)
            verify_clean()

    # ---- REPORT ----
    logger.info("Generating report for PR #%d...", pr_number)

    # Determine verdict from analysis history
    history = pr.get("analysis_history", [])
    bare_verdict = history[0].get("bare_verdict", "needs_improvement") if history else "needs_improvement"
    wolfden_baseline_verdict = history[0].get("wolfden_verdict", "needs_improvement") if history else "needs_improvement"
    wolfden_final_verdict = history[-1].get("wolfden_verdict", "needs_improvement") if history else "needs_improvement"

    # Verdict-based delta logic
    baseline_rank = _VERDICT_RANK.get(wolfden_baseline_verdict, 1)
    final_rank = _VERDICT_RANK.get(wolfden_final_verdict, 1)
    if final_rank > baseline_rank:
        verdict = "improved"
    elif final_rank < baseline_rank:
        verdict = "regressed"
    else:
        verdict = "neutral"

    # Build analyses list for report from state history
    report_analyses = []
    for entry in history:
        report_analyses.append({
            "bare_verdict": entry.get("bare_verdict", "?"),
            "wolfden_verdict": entry.get("wolfden_verdict", "?"),
            "distilled_summary": entry.get("distilled_summary", ""),
            "findings": [],
            "root_causes": [],
        })

    # Save raw responses alongside the report for review
    from pathlib import Path
    reports_dir = Path(REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    bare_text = pr.get("bare_result", {}).get("response", "") or ""
    wolfden_texts = [r.get("response", "") or "" for r in pr.get("wolfden_results", [])]

    (reports_dir / f"pr-{pr_number}-bare.md").write_text(
        f"# Bare Claude Response — PR #{pr_number}\n\n{bare_text}\n"
    )
    for i, wt in enumerate(wolfden_texts):
        label = "baseline" if i == 0 else f"iter{i}"
        (reports_dir / f"pr-{pr_number}-wolfden-{label}.md").write_text(
            f"# wolfDen Claude Response ({label}) — PR #{pr_number}\n\n{wt}\n"
        )

    generate_pr_report(
        pr_number=pr_number,
        repo=repo,
        pr_title=pr_data.get("title", ""),
        problem_desc=problem_desc,
        analyses=report_analyses,
        improvements=pr.get("improvements", []),
        verdict=verdict,
    )

    complete_pr(state, verdict, bare_verdict, wolfden_baseline_verdict, wolfden_final_verdict)
    save_state(state)

    logger.info(
        "PR #%d complete: verdict=%s, bare=%s, wolfDen=%s->%s",
        pr_number, verdict, bare_verdict, wolfden_baseline_verdict, wolfden_final_verdict,
    )


def main():
    _setup_logging()

    parser = argparse.ArgumentParser(description="wolfDen EDD loop")
    parser.add_argument("--iterations", type=int, default=2,
                        help="Improvement iterations per PR (default: 2)")
    parser.add_argument("--review", action="store_true",
                        help="Write proposals for review instead of auto-applying")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from state file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without executing")
    parser.add_argument("--repo", default="wolfssl/wolfssl",
                        help="GitHub repo for PR candidates")
    parser.add_argument("--pr", type=int, default=None,
                        help="Evaluate a specific PR number")
    parser.add_argument("--model", default="opus",
                        help="Claude model for analysis/improvement")
    parser.add_argument("--eval-model", default="opus",
                        help="Claude model for eval runs")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number of PRs to fetch for candidate selection")
    args = parser.parse_args()

    # Check eval server
    if not args.dry_run:
        if not check_server_health():
            logger.error(
                "Eval server not running. Start it first:\n"
                "  python -m scripts.edd.eval_server &"
            )
            sys.exit(1)
        logger.info("Eval server is healthy")

    # Load or initialize state
    if args.resume:
        state = load_state()
        if state["status"] == "idle" and not state.get("current_pr"):
            logger.info("No state to resume from. Starting fresh.")
            args.resume = False
            state = _empty_state(args.iterations)
        else:
            logger.info("Resuming from state file")
    else:
        # Preserve completed_prs from previous runs so we don't re-evaluate
        prev_state = load_state()
        prev_completed = prev_state.get("completed_prs", [])
        state = _empty_state(args.iterations)
        if prev_completed:
            state["completed_prs"] = prev_completed
            logger.info("Preserved %d completed PRs from previous runs", len(prev_completed))

    # ---- Candidate Selection ----
    if args.pr:
        # Specific PR mode — add to queue if no current PR
        if not state.get("current_pr"):
            state["candidate_queue"] = [{"pr_number": args.pr, "repo": args.repo}]
    elif not args.resume and not state.get("current_pr"):
        logger.info("Fetching PR candidates from %s...", args.repo)
        prs = fetch_merged_prs(repo=args.repo, limit=args.limit)
        candidates = filter_candidates(prs, state.get("completed_prs", []))
        logger.info("Found %d candidates from %d PRs", len(candidates), len(prs))

        if not candidates:
            logger.info("No suitable candidates found")
            return

        selected = select_diverse_candidate(candidates, state.get("completed_prs", []))
        if selected:
            state["candidate_queue"] = [{
                "pr_number": selected["number"],
                "repo": args.repo,
            }]
            logger.info(
                "Selected PR #%d: %s [%s]",
                selected["number"], selected["title"],
                selected.get("_category", "?"),
            )

    if args.dry_run:
        logger.info("Dry run — state would be:")
        print(json.dumps(state, indent=2))
        return

    # ---- Main Loop ----
    state["status"] = "running"
    save_state(state)

    # Pop next candidate if no current PR
    if not state.get("current_pr"):
        candidate = pop_next_candidate(state)
        if not candidate:
            logger.info("No candidates to evaluate")
            state["status"] = "idle"
            save_state(state)
            return
        save_state(state)

    # Run eval for current PR
    try:
        run_pr_eval(
            state,
            iterations=args.iterations,
            auto_apply=not args.review,
            model=args.model,
            eval_model=args.eval_model,
        )
    except Exception as e:
        logger.exception("Unexpected error in eval loop")
        log_error(state, f"Unexpected: {e}")
        save_state(state)

    # ---- Summary ----
    if state.get("completed_prs"):
        all_improvements = []
        for completed in state["completed_prs"]:
            for imp in completed.get("improvements", []):
                imp_with_pr = dict(imp, pr_number=completed.get("pr_number", "?"))
                all_improvements.append(imp_with_pr)
        generate_summary_report(state["completed_prs"], all_improvements)

    state["status"] = "completed"
    save_state(state)
    logger.info("EDD loop complete")


if __name__ == "__main__":
    main()

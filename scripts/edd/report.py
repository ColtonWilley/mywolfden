from __future__ import annotations

"""Markdown report generation for wolfDen EDD loop.

Per-PR reports with three-way comparison and summary reports.
Uses verdicts (pass/needs_improvement/fail) instead of numeric scores.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from . import REPORTS_DIR

logger = logging.getLogger(__name__)


def _ensure_reports_dir() -> Path:
    d = Path(REPORTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_pr_report(
    pr_number: int,
    repo: str,
    pr_title: str,
    problem_desc: dict,
    analyses: list[dict],
    improvements: list[dict],
    verdict: str,
) -> str:
    """Generate a per-PR eval report.

    Returns path to the written report file.
    """
    reports_dir = _ensure_reports_dir()
    filepath = reports_dir / f"pr-{pr_number}.md"

    lines = [
        f"# Eval Report: PR #{pr_number}",
        "",
        f"**Repo:** {repo}",
        f"**PR Title:** {pr_title}",
        f"**Problem:** {problem_desc.get('title', '?')} (source: {problem_desc.get('source', '?')})",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"**Verdict:** {verdict}",
        "",
    ]

    # Verdict table
    if analyses:
        lines.append("## Verdicts")
        lines.append("")

        headers = ["Pillar", "Bare"]
        for i in range(len(analyses)):
            label = "wolfDen" if i == 0 else f"wolfDen (iter {i})"
            headers.append(label)
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        baseline = analyses[0]

        # Overall verdict row
        row = ["**Overall**"]
        row.append(f"**{baseline.get('bare_verdict', '?')}**")
        for analysis in analyses:
            row.append(f"**{analysis.get('wolfden_verdict', '?')}**")
        lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    # wolfDen advantage
    if analyses:
        advantage = analyses[0].get("wolfden_advantage", "")
        if advantage and advantage.lower() != "none":
            lines.append("## wolfDen Advantage")
            lines.append("")
            lines.append(advantage)
            lines.append("")

    # Analysis details per iteration
    lines.append("## Analysis Details")
    lines.append("")

    for i, analysis in enumerate(analyses):
        label = "Baseline" if i == 0 else f"Iteration {i}"
        bare_v = analysis.get("bare_verdict", "?")
        wd_v = analysis.get("wolfden_verdict", "?")
        lines.append(f"### {label} (bare: {bare_v}, wolfden: {wd_v})")
        lines.append("")

        findings = analysis.get("findings", [])
        if findings:
            lines.append("**Findings:**")
            for f in findings:
                severity = f.get("severity", "?")
                category = f.get("category", "?")
                desc = f.get("description", "?")
                lines.append(f"- [{severity}] **{category}**: {desc}")
            lines.append("")

        summary = analysis.get("distilled_summary", "")
        if summary:
            lines.append(f"**Summary:** {summary}")
            lines.append("")

        # Changes applied for this iteration
        iter_improvements = [imp for imp in improvements if imp.get("iteration") == i]
        if iter_improvements:
            lines.append("**Changes applied:**")
            for imp in iter_improvements:
                lines.append(f"- `{imp.get('file', '?')}` — {imp.get('description', '?')}")
            lines.append("")

    # Remaining root causes
    if analyses:
        root_causes = analyses[-1].get("root_causes", [])
        if root_causes:
            lines.append("## Remaining Knowledge Gaps")
            lines.append("")
            for rc in root_causes:
                lines.append(f"- {rc}")
            lines.append("")

    filepath.write_text("\n".join(lines) + "\n")
    logger.info("Wrote PR report: %s", filepath)
    return str(filepath)


def generate_summary_report(completed_prs: list[dict], all_improvements: list[dict]) -> str:
    """Generate a cross-PR summary report."""
    reports_dir = _ensure_reports_dir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = reports_dir / f"summary-{today}.md"

    lines = [
        f"# wolfDen EDD Summary — {today}",
        "",
        "## PRs Evaluated",
        "",
        "| PR | Repo | Bare | wolfDen Baseline | wolfDen Final | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for pr in completed_prs:
        num = pr.get("pr_number", "?")
        repo = pr.get("repo", "?")
        # Support both old score-based and new verdict-based entries
        bare = pr.get("bare_verdict", pr.get("bare_score", "?"))
        wd_base = pr.get("wolfden_baseline_verdict", pr.get("wolfden_baseline", "?"))
        wd_final = pr.get("wolfden_final_verdict", pr.get("wolfden_final", "?"))
        verdict = pr.get("verdict", "?")
        lines.append(f"| #{num} | {repo} | {bare} | {wd_base} | {wd_final} | {verdict} |")

    lines.append("")

    if all_improvements:
        lines.append("## Changes Applied")
        lines.append("")
        lines.append("| File | Change | PR | Iteration |")
        lines.append("| --- | --- | --- | --- |")
        for imp in all_improvements:
            lines.append(f"| `{imp.get('file', '?')}` | {imp.get('description', '?')} | #{imp.get('pr_number', '?')} | {imp.get('iteration', '?')} |")
        lines.append("")

    if completed_prs:
        # Verdict distribution
        improved = sum(1 for p in completed_prs if p.get("verdict") == "improved")
        regressed = sum(1 for p in completed_prs if p.get("verdict") == "regressed")
        neutral = sum(1 for p in completed_prs if p.get("verdict") == "neutral")
        failed = sum(1 for p in completed_prs if p.get("verdict") == "failed")

        # wolfDen verdict distribution
        wd_pass = 0
        wd_ni = 0
        wd_fail = 0
        for p in completed_prs:
            final = p.get("wolfden_final_verdict", "")
            if final == "pass":
                wd_pass += 1
            elif final == "needs_improvement":
                wd_ni += 1
            elif final == "fail":
                wd_fail += 1

        lines.append("## Aggregate")
        lines.append("")
        lines.append(f"- Total PRs: {len(completed_prs)}")
        lines.append(f"- Improved: {improved}")
        lines.append(f"- Neutral: {neutral}")
        lines.append(f"- Regressed: {regressed}")
        if failed:
            lines.append(f"- Failed (errors): {failed}")
        lines.append("")
        lines.append("### wolfDen Final Verdict Distribution")
        lines.append("")
        lines.append(f"- Pass: {wd_pass}/{len(completed_prs)}")
        lines.append(f"- Needs Improvement: {wd_ni}/{len(completed_prs)}")
        lines.append(f"- Fail: {wd_fail}/{len(completed_prs)}")
        lines.append("")

    filepath.write_text("\n".join(lines) + "\n")
    logger.info("Wrote summary report: %s", filepath)
    return str(filepath)

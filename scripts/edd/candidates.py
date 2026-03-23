from __future__ import annotations

"""PR candidate selection for wolfDen EDD.

Fetches merged PRs via gh CLI, filters for good eval candidates,
extracts problem descriptions, and scores for diversity.
"""

import json
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

# PR fields to fetch from GitHub
_PR_FIELDS = "number,title,body,labels,files,mergedAt,mergeCommit,baseRefName,headRefName,url"

# File count bounds for candidate selection
_MIN_CHANGED_FILES = 1
_MAX_CHANGED_FILES = 50

# Patterns that indicate automated/trivial PRs
_SKIP_TITLE_PATTERNS = [
    re.compile(r"^bump\b", re.I),
    re.compile(r"^update\s+dependenc", re.I),
    re.compile(r"\bci\b.*\bfix\b", re.I),
    re.compile(r"^merge\b", re.I),
]

# Patterns for docs-only PRs
_DOCS_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}

# Categories for diversity scoring
_CATEGORIES = {
    "crypto": ["wolfcrypt/src/", "wolfssl/wolfcrypt/"],
    "tls": ["src/internal.c", "src/ssl.c", "src/tls", "src/dtls"],
    "asn": ["wolfcrypt/src/asn.c", "wolfssl/wolfcrypt/asn"],
    "platform": ["IDE/", "port/", "platform/"],
    "build": ["configure.ac", "CMakeLists", "Makefile", "m4/"],
    "test": ["tests/", "testsuite/"],
    "integration": ["wrapper/", "osp/"],
}


def _gh(args: list[str], timeout: int = 30) -> str:
    """Run a gh CLI command."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"gh command timed out: {' '.join(args[:3])}") from e

    if result.returncode != 0:
        stderr = result.stderr.strip()[:500]
        raise RuntimeError(f"gh failed: {stderr}")

    return result.stdout.strip()


def fetch_merged_prs(repo: str = "wolfssl/wolfssl", limit: int = 30) -> list[dict]:
    """Fetch recent merged PRs from a GitHub repo."""
    raw = _gh([
        "pr", "list",
        "--repo", repo,
        "--state", "merged",
        "--limit", str(limit),
        "--json", _PR_FIELDS,
    ])
    return json.loads(raw)


def fetch_pr_detail(pr_number: int, repo: str = "wolfssl/wolfssl") -> dict:
    """Fetch detailed PR data including diff."""
    raw = _gh([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", f"{_PR_FIELDS},additions,deletions,reviews,comments",
    ])
    return json.loads(raw)


def fetch_pr_diff(pr_number: int, repo: str = "wolfssl/wolfssl") -> str:
    """Fetch the PR diff."""
    return _gh([
        "pr", "diff", str(pr_number),
        "--repo", repo,
    ], timeout=60)


def fetch_issue(issue_number: int, repo: str = "wolfssl/wolfssl") -> dict:
    """Fetch an issue's details."""
    raw = _gh([
        "issue", "view", str(issue_number),
        "--repo", repo,
        "--json", "number,title,body,labels",
    ])
    return json.loads(raw)


def _categorize_pr(pr: dict) -> str:
    """Categorize a PR by the files it touches."""
    files = pr.get("files", [])
    file_paths = [f.get("path", "") for f in files]

    # Score each category
    scores: dict[str, int] = {}
    for category, patterns in _CATEGORIES.items():
        count = sum(
            1 for fp in file_paths
            for pat in patterns if pat in fp
        )
        if count > 0:
            scores[category] = count

    if not scores:
        return "other"
    return max(scores, key=scores.get)


def _is_docs_only(pr: dict) -> bool:
    """Check if a PR only touches documentation files."""
    files = pr.get("files") or []
    if not files:
        return False  # Unknown file list — don't skip
    for f in files:
        path = f.get("path", "")
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext not in _DOCS_EXTENSIONS:
            return False
    return True


def _should_skip(pr: dict) -> bool:
    """Check if a PR should be skipped for eval."""
    title = pr.get("title", "")

    for pattern in _SKIP_TITLE_PATTERNS:
        if pattern.search(title):
            return True

    files = pr.get("files", [])
    n_files = len(files)
    if n_files < _MIN_CHANGED_FILES or n_files > _MAX_CHANGED_FILES:
        return True

    if _is_docs_only(pr):
        return True

    return False


def extract_problem_description(pr: dict, repo: str = "wolfssl/wolfssl") -> dict:
    """Extract a natural problem description from a PR.

    Returns {title, body} where body is the problem statement
    suitable for a simple developer prompt.
    """
    body = pr.get("body", "") or ""

    # Check for linked issues: "Fixes #123", "Closes #456"
    issue_refs = re.findall(r"(?:fix(?:es)?|close[sd]?|resolve[sd]?)\s+#(\d+)", body, re.I)
    if issue_refs:
        try:
            issue = fetch_issue(int(issue_refs[0]), repo=repo)
            return {
                "title": issue.get("title", pr.get("title", "")),
                "body": issue.get("body", "") or "",
                "source": f"issue #{issue_refs[0]}",
            }
        except RuntimeError:
            logger.warning("Failed to fetch linked issue #%s", issue_refs[0])

    # Extract problem from PR body if it has structured sections
    # Look for "Problem:", "Bug:", "Before:", "Issue:" sections
    for marker in ("## problem", "## bug", "## issue", "problem:", "bug:", "before this"):
        idx = body.lower().find(marker)
        if idx != -1:
            # Extract text until next section header or end
            rest = body[idx:]
            # Search for next header after the marker itself
            next_header = re.search(r"\n##\s", rest[len(marker):])
            if next_header:
                section = rest[:next_header.start() + len(marker)]
            else:
                section = rest
            return {
                "title": pr.get("title", ""),
                "body": section.strip(),
                "source": "pr_body_section",
            }

    # Fallback: use the full PR body as context
    return {
        "title": pr["title"],
        "body": body[:2000] if body else "",
        "source": "pr_body",
    }


def filter_candidates(
    prs: list[dict],
    completed_prs: list[dict],
) -> list[dict]:
    """Filter PRs to good eval candidates."""
    completed_numbers = {p.get("pr_number") for p in completed_prs}

    candidates = []
    for pr in prs:
        if pr["number"] in completed_numbers:
            continue
        if _should_skip(pr):
            continue
        if not pr.get("mergeCommit"):
            continue

        pr["_category"] = _categorize_pr(pr)
        candidates.append(pr)

    return candidates


def select_diverse_candidate(
    candidates: list[dict],
    completed_prs: list[dict],
) -> dict | None:
    """Pick a candidate maximizing diversity across categories.

    Prefers categories that have been evaluated least.
    """
    if not candidates:
        return None

    # Count completed per category
    category_counts: dict[str, int] = {}
    for pr in completed_prs:
        cat = pr.get("category", "other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Score: lower is better (prefer underrepresented categories)
    scored = []
    for pr in candidates:
        cat = pr.get("_category", "other")
        score = category_counts.get(cat, 0)
        # Prefer PRs with linked issues (better problem descriptions)
        body = pr.get("body", "") or ""
        if re.search(r"(?:fix(?:es)?|close[sd]?|resolve[sd]?)\s+#\d+", body, re.I):
            score -= 2  # Bonus for linked issues
        scored.append((score, pr))

    scored.sort(key=lambda x: x[0])
    return scored[0][1]

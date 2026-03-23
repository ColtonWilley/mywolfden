from __future__ import annotations

"""LLM improvement proposals targeting wolfDen knowledge files.

Takes analysis findings, reads relevant rules files, asks claude -p
to propose targeted changes, and optionally applies them.
"""

import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from . import WOLFDEN_DIR, PROMPTS_DIR
from .llm import call_claude_json

logger = logging.getLogger(__name__)

_jinja_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)

# Base path for all rules files
_RULES_BASE = Path(WOLFDEN_DIR) / "scaffold" / ".claude" / "rules"

# Paths the improver is allowed to write to (relative to WOLFDEN_DIR).
# Order matters: more specific dirs first so the broad fallback doesn't
# short-circuit validation.
_ALLOWED_DIRS = [
    "scaffold/.claude/rules/platforms",
    "scaffold/.claude/rules/products",
    "scaffold/.claude/rules/crypto",
    "scaffold/.claude/rules/integrations",
    "scaffold/.claude/rules",
]

# Files that are off-limits
_BLOCKED_FILES = {
    "scaffold/.claude/settings.json",
    "scaffold/.hooks/scan-repos.sh",
    "scaffold/setup.sh",
    "scaffold/.claude/rules/discovered-patterns.md",
}

# Map root cause keywords to likely relevant files
_ROOT_CAUSE_FILE_MAP = {
    "investigation": ["scaffold/.claude/rules/investigation-methods.md"],
    "methodology": ["scaffold/.claude/rules/investigation-methods.md"],
    "verification": ["scaffold/.claude/rules/investigation-methods.md"],
    "build system": ["scaffold/.claude/rules/build-system.md", "scaffold/.claude/rules/configure-dependencies.md"],
    "configure": ["scaffold/.claude/rules/build-system.md", "scaffold/.claude/rules/configure-dependencies.md"],
    "coding standard": ["scaffold/.claude/rules/coding-standards.md"],
    "implementation": ["scaffold/.claude/rules/implementation-patterns.md"],
    "error": ["scaffold/.claude/rules/error-taxonomy.md", "scaffold/.claude/rules/error-resolutions.md"],
    "embedded": ["scaffold/.claude/rules/embedded-integration-checklist.md"],
    "version": ["scaffold/.claude/rules/version-gotchas.md"],
    # Crypto topics
    "tls": ["scaffold/.claude/rules/crypto/tls-handshake.md"],
    "dtls": ["scaffold/.claude/rules/crypto/dtls.md"],
    "certificate": ["scaffold/.claude/rules/crypto/certificates.md"],
    "fips": ["scaffold/.claude/rules/crypto/fips-patterns.md"],
    "side channel": ["scaffold/.claude/rules/crypto/side-channel-attacks.md"],
    "assembly": ["scaffold/.claude/rules/crypto/compiler-toolchain-assembly.md"],
}

_MAX_FILE_CHARS = 8000

# Keywords in reasoning/content that indicate a non-technical (out-of-scope) proposal.
# These should never appear in wolfDen knowledge improvements.
_NON_TECHNICAL_KEYWORDS = [
    "customer communication", "support ticket", "ticket lifecycle",
    "workflow", "presales", "intake", "escalation",
    "reply format", "tone", "politeness",
    "sales", "business process",
]


def _count_leading_hashes(line: str) -> int:
    """Count leading '#' characters for markdown header level."""
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#"))


def _validate_path(file_path: str) -> bool:
    """Check if a file path is allowed and not blocked."""
    if file_path in _BLOCKED_FILES:
        logger.warning("Blocked file: %s", file_path)
        return False
    if not any(file_path.startswith(d) for d in _ALLOWED_DIRS):
        logger.warning("File outside allowed dirs: %s", file_path)
        return False
    # Path traversal guard
    full_path = (Path(WOLFDEN_DIR) / file_path).resolve()
    if not str(full_path).startswith(str(Path(WOLFDEN_DIR).resolve())):
        logger.error("Path traversal blocked: %s", file_path)
        return False
    return True


def _identify_relevant_files(root_causes: list[str], findings: list[dict]) -> list[str]:
    """Determine which rules files to include based on root causes."""
    files = set()

    for cause in root_causes:
        cause_lower = cause.lower()
        for keyword, paths in _ROOT_CAUSE_FILE_MAP.items():
            if keyword in cause_lower:
                files.update(paths)

        # Dynamic platform/product lookup
        for prefix in ("platform", "product"):
            if prefix in cause_lower:
                for word in cause_lower.split():
                    if prefix == "platform":
                        search_dir = _RULES_BASE / "platforms"
                    else:
                        search_dir = _RULES_BASE / "products"
                    if search_dir.exists():
                        matches = list(search_dir.glob(f"*{word}*"))
                        for m in matches[:2]:
                            files.add(str(m.relative_to(Path(WOLFDEN_DIR))))

    # Also check findings
    for finding in findings:
        desc = finding.get("description", "").lower()
        for keyword, paths in _ROOT_CAUSE_FILE_MAP.items():
            if keyword in desc:
                files.update(paths)

    # Default to investigation-methods if nothing matched
    if not files:
        files.add("scaffold/.claude/rules/investigation-methods.md")

    return sorted(files)[:5]


def _read_file_content(relative_path: str) -> str | None:
    """Read file content, truncating if too large."""
    full_path = Path(WOLFDEN_DIR) / relative_path
    if not full_path.exists():
        return None
    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Cannot read non-UTF-8 file: %s", relative_path)
        return None
    if len(content) > _MAX_FILE_CHARS:
        content = content[:_MAX_FILE_CHARS] + f"\n\n... [truncated at {_MAX_FILE_CHARS} chars]"
    return content


def propose_improvements(
    findings: list[dict],
    root_causes: list[str],
    pr_context: str = "",
    wolfden_advantage: str = "",
    model: str = "opus",
) -> list[dict]:
    """Ask LLM to propose improvements based on analysis findings.

    Returns list of validated proposal dicts.
    """
    relevant_paths = _identify_relevant_files(root_causes, findings)
    relevant_files = []
    for rp in relevant_paths:
        content = _read_file_content(rp)
        if content is not None:
            relevant_files.append({"path": rp, "content": content})

    template = _jinja_env.get_template("improvement.md")
    rendered = template.render(
        findings_json=json.dumps(findings, indent=2),
        root_causes_json=json.dumps(root_causes, indent=2),
        pr_context=pr_context or "Not provided.",
        wolfden_advantage=wolfden_advantage or "Not assessed.",
        relevant_files=relevant_files,
    )

    result = call_claude_json(rendered, model=model, timeout=600)

    proposals = result.get("proposals", [])
    logger.info("Received %d proposal(s)", len(proposals))

    # Validate proposals
    validated = []
    for p in proposals[:2]:
        if not _validate_path(p.get("file", "")):
            continue

        # Reject non-technical proposals
        reasoning_text = (p.get("reasoning", "") + " " + p.get("content", "")).lower()
        non_tech_hits = [kw for kw in _NON_TECHNICAL_KEYWORDS if kw in reasoning_text]
        if non_tech_hits:
            logger.warning("Skipping non-technical proposal for %s (keywords: %s)",
                           p.get("file", "?"), ", ".join(non_tech_hits))
            continue

        validated.append(p)

    return validated


def apply_proposal(proposal: dict) -> bool:
    """Apply a single improvement proposal to disk. Returns True on success."""
    file_path = proposal.get("file", "")
    action = proposal.get("action", "")
    anchor = proposal.get("anchor", "")
    content = proposal.get("content", "")

    # Re-validate path (apply_proposal may be called independently)
    if not _validate_path(file_path):
        return False

    full_path = (Path(WOLFDEN_DIR) / file_path).resolve()

    if action == "new_file":
        if full_path.exists():
            logger.warning("new_file target already exists: %s", file_path)
            return False
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        logger.info("Created new file: %s", file_path)
        return True

    if not full_path.exists():
        logger.error("File not found: %s", file_path)
        return False

    existing = full_path.read_text(encoding="utf-8")

    if action == "append_section":
        if existing and not existing.endswith("\n"):
            existing += "\n"
        full_path.write_text(existing + "\n" + content + "\n", encoding="utf-8")
        logger.info("Appended to: %s", file_path)
        return True

    if action == "insert_after":
        if not anchor:
            logger.error("insert_after requires anchor text")
            return False
        idx = existing.find(anchor)
        if idx == -1:
            logger.error("Anchor not found in %s: %s", file_path, anchor[:80])
            return False
        insert_point = idx + len(anchor)
        newline_after = existing.find("\n", insert_point)
        if newline_after == -1:
            insert_point = len(existing)
        else:
            insert_point = newline_after
        updated = existing[:insert_point] + "\n" + content + existing[insert_point:]
        full_path.write_text(updated, encoding="utf-8")
        logger.info("Inserted after anchor in: %s", file_path)
        return True

    if action == "replace_lines":
        if not anchor:
            logger.error("replace_lines requires anchor (section header)")
            return False
        idx = existing.find(anchor)
        if idx == -1:
            logger.error("Section header not found in %s: %s", file_path, anchor[:80])
            return False
        level = _count_leading_hashes(anchor)
        search_from = idx + len(anchor)
        next_section = len(existing)
        lines = existing[search_from:].split("\n")
        offset = search_from
        for line in lines:
            if line.lstrip().startswith("#") and offset > search_from:
                header_level = _count_leading_hashes(line)
                if header_level <= level:
                    next_section = offset
                    break
            offset += len(line) + 1
        updated = existing[:idx] + anchor + "\n" + content + "\n" + existing[next_section:]
        full_path.write_text(updated, encoding="utf-8")
        logger.info("Replaced section in: %s", file_path)
        return True

    logger.error("Unknown action: %s", action)
    return False


def write_proposal_for_review(proposal: dict, reports_dir: str,
                               pr_number: int, iteration: int) -> str:
    """Write a proposal to disk for human review."""
    proposals_dir = Path(reports_dir) / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    filename = f"pr-{pr_number}-iter{iteration}-{proposal.get('file', 'unknown').replace('/', '_')}.md"
    filepath = proposals_dir / filename

    lines = [
        f"# Improvement Proposal: PR #{pr_number}, Iteration {iteration}",
        "",
        f"**File:** `{proposal.get('file', '?')}`",
        f"**Action:** `{proposal.get('action', '?')}`",
        f"**Anchor:** `{proposal.get('anchor', 'N/A')}`",
        "",
        "## Reasoning",
        proposal.get("reasoning", "No reasoning provided."),
        "",
        "## Proposed Content",
        "```",
        proposal.get("content", ""),
        "```",
    ]

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote proposal for review: %s", filepath)
    return str(filepath)

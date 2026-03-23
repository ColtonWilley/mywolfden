"""Sync knowledge files from support-knowledge into the wolfDen scaffold.

Reads the sync-manifest.json, converts HTML comment metadata to YAML frontmatter
with paths: globs, and optionally runs claude -p for content reframing.

Usage:
    python sync_knowledge.py --source /path/to/knowledge  # Explicit source
    python sync_knowledge.py                   # Full sync (uses WOLFDEN_KNOWLEDGE_SOURCE env var)
    python sync_knowledge.py --dry-run         # Show what would be synced
    python sync_knowledge.py --reframe-only    # Only process files needing reframing
    python sync_knowledge.py --force           # Re-sync even if source unchanged
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "sync-manifest.json"
OUTPUT_DIR = SCRIPT_DIR / "scaffold" / ".claude" / "rules"
STATE_PATH = SCRIPT_DIR / "sync-state.json"
DISTILLATION_PROMPT_PATH = SCRIPT_DIR / "distillation_prompt.md"


def _resolve_knowledge_source(cli_source: str | None = None) -> Path:
    """Resolve knowledge source directory, checking multiple locations."""
    if cli_source:
        return Path(cli_source)
    if env := os.environ.get("WOLFDEN_KNOWLEDGE_SOURCE"):
        return Path(env)
    # Legacy monorepo layout (wolfssl-llm-bots cloned alongside mywolfden)
    legacy = SCRIPT_DIR.parent / "wolfssl-llm-bots" / "apps" / "support-knowledge" / "knowledge"
    if legacy.exists():
        return legacy
    raise SystemExit(
        "Knowledge source not found.\n"
        "Set WOLFDEN_KNOWLEDGE_SOURCE env var or pass --source PATH.\n"
        "This should point to the apps/support-knowledge/knowledge/ directory "
        "from the wolfssl-llm-bots repo."
    )

# Light reframe replacements (no LLM needed)
LIGHT_REPLACEMENTS = [
    (r"\bcustomer\b", "user"),
    (r"\bthe customer\b", "the user"),
    (r"\bCustomer\b", "User"),
    (r"\bsupport ticket\b", "issue"),
    (r"\bSupport ticket\b", "Issue"),
    (r"\bticket\b", "issue"),
    (r"\bTicket\b", "Issue"),
    (r'code_search\([^)]*\)', "Grep"),
    (r"\bcode_search\b", "Grep"),
    (r"\bread_file\b", "Read"),
    (r"\bvector_search\b", "search"),
    (r"\bget_summary\b", "look up"),
    (r"\bdoc_search\b", "search documentation"),
]


def load_manifest() -> dict:
    """Load the sync manifest."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_state() -> dict:
    """Load sync state (tracks last-modified times)."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    """Save sync state."""
    STATE_PATH.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_html_metadata(content: str) -> dict[str, str]:
    """Extract metadata from HTML comment tags (<!-- key: value -->)."""
    metadata = {}
    for match in re.finditer(r"<!--\s*(\w+):\s*(.+?)\s*-->", content):
        key, value = match.group(1), match.group(2).strip()
        metadata[key] = value
    return metadata


def strip_html_comments(content: str) -> str:
    """Remove HTML comment metadata lines from content."""
    return re.sub(r"<!--.*?-->\n?", "", content).lstrip("\n")


def build_yaml_frontmatter(paths: list[str]) -> str:
    """Build YAML frontmatter with paths globs."""
    if not paths:
        return ""
    lines = ["---", "paths:"]
    for p in paths:
        lines.append(f'  - "{p}"')
    lines.append("---", )
    return "\n".join(lines) + "\n\n"


def apply_light_reframe(content: str) -> str:
    """Apply regex-based light reframing (no LLM)."""
    for pattern, replacement in LIGHT_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    # Fix article grammar: "a issue" -> "an issue", "a error" -> "an error"
    content = re.sub(r'\ba (issue|error|investigation)\b', r'an \1', content)
    content = re.sub(r'\bA (issue|error|investigation)\b', r'An \1', content)
    return content


def distill_with_claude(content: str, source_name: str) -> str | None:
    """Run heavy reframing via claude -p --model opus."""
    if not DISTILLATION_PROMPT_PATH.exists():
        logger.warning("Distillation prompt not found at %s", DISTILLATION_PROMPT_PATH)
        return None

    prompt = DISTILLATION_PROMPT_PATH.read_text(encoding="utf-8")
    full_input = (
        f"{prompt}\n\n"
        f"---\n\n"
        f"Source file: {source_name}\n\n"
        f"Content to reframe:\n\n{content}"
    )

    logger.info("  Running claude -p for heavy reframe of %s...", source_name)
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "opus", "--output-format", "text"],
            input=full_input,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            logger.error("  claude -p failed: %s", result.stderr[:200] if result.stderr else "no output")
            return None
    except FileNotFoundError:
        logger.error("  'claude' CLI not found. Install Claude Code or add to PATH.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("  claude -p timed out after 180s for %s", source_name)
        return None


def sync_file(entry: dict, knowledge_source: Path, force: bool = False,
              dry_run: bool = False, state: dict | None = None) -> bool:
    """Sync a single knowledge file. Returns True if file was written."""
    source_path = knowledge_source / entry["source"]
    output_path = OUTPUT_DIR / entry["output"]
    reframe = entry.get("reframe", "none")
    paths_globs = entry.get("paths", [])

    if not source_path.exists():
        logger.warning("  Source not found: %s", source_path)
        return False

    # Check if source has changed
    mtime = str(source_path.stat().st_mtime)
    state_key = entry["source"]
    if state and not force:
        if state.get(state_key) == mtime and output_path.exists():
            return False

    if dry_run:
        logger.info("  [dry-run] Would sync: %s -> %s (reframe=%s)",
                     entry["source"], entry["output"], reframe)
        return False

    # Read and process source
    content = source_path.read_text(encoding="utf-8")
    content = strip_html_comments(content)

    # Apply reframing
    if reframe == "light":
        content = apply_light_reframe(content)
    elif reframe == "heavy":
        result = distill_with_claude(content, entry["source"])
        if result:
            content = result
        else:
            logger.warning("  Heavy reframe failed for %s, using light reframe fallback",
                          entry["source"])
            content = apply_light_reframe(content)

    # Build output with frontmatter
    frontmatter = build_yaml_frontmatter(paths_globs)
    output = frontmatter + content

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")

    # Update state
    if state is not None:
        state[state_key] = mtime

    logger.info("  [synced] %s -> %s", entry["source"], entry["output"])
    return True


def main():
    parser = argparse.ArgumentParser(description="Sync knowledge to wolfDen")
    parser.add_argument("--source", type=str, default=None,
                       help="Path to support-knowledge/knowledge/ directory")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be synced without writing files")
    parser.add_argument("--force", action="store_true",
                       help="Re-sync all files even if unchanged")
    parser.add_argument("--reframe-only", action="store_true",
                       help="Only process files that need reframing (light or heavy)")
    args = parser.parse_args()

    knowledge_source = _resolve_knowledge_source(args.source)

    manifest = load_manifest()
    state = load_state()
    files = manifest["files"]

    if args.reframe_only:
        files = [f for f in files if f.get("reframe", "none") != "none"]

    logger.info("Syncing %d knowledge files (source: %s)", len(files), knowledge_source)
    logger.info("Output: %s", OUTPUT_DIR)

    synced = 0
    skipped = 0
    errors = 0

    for entry in files:
        try:
            if sync_file(entry, knowledge_source, force=args.force,
                        dry_run=args.dry_run, state=state):
                synced += 1
            else:
                skipped += 1
        except Exception as e:
            logger.error("  Error processing %s: %s", entry["source"], e)
            errors += 1

    if not args.dry_run:
        save_state(state)

    logger.info("Done: %d synced, %d unchanged, %d errors", synced, skipped, errors)


if __name__ == "__main__":
    main()

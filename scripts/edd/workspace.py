from __future__ import annotations

"""Git time-travel for eval workspace.

Checks out the wolfssl repo at a pre-PR commit so Claude evaluates against
the codebase as it existed before the fix. Always restores on cleanup.
"""

import logging
import subprocess

from . import WOLFSSL_REPO

logger = logging.getLogger(__name__)


class WorkspaceError(Exception):
    """Git workspace operation failed."""


def _git(args: list[str], timeout: int = 60) -> str:
    """Run a git command in the wolfssl repo."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=timeout,
            cwd=WOLFSSL_REPO,
        )
    except subprocess.TimeoutExpired as e:
        raise WorkspaceError(f"git {args[0]} timed out after {timeout}s") from e

    if result.returncode != 0:
        stderr = result.stderr.strip()[:500]
        raise WorkspaceError(f"git {' '.join(args[:2])} failed: {stderr}")

    return result.stdout.strip()


def get_current_ref() -> str:
    """Get the current HEAD ref (branch name or commit hash)."""
    try:
        return _git(["symbolic-ref", "--short", "HEAD"])
    except WorkspaceError:
        return _git(["rev-parse", "HEAD"])


def fetch_origin() -> None:
    """Fetch latest from origin."""
    logger.info("Fetching origin in wolfssl repo...")
    _git(["fetch", "origin"], timeout=120)


def commit_exists(commit: str) -> bool:
    """Check if a commit exists in the local repo."""
    try:
        _git(["cat-file", "-t", commit])
        return True
    except WorkspaceError:
        return False


def setup_workspace(merge_commit: str) -> dict:
    """Checkout the parent of a merge commit for evaluation.

    Args:
        merge_commit: The PR's merge commit SHA.

    Returns:
        Context dict with original_ref and base_commit for teardown.
    """
    # Verify no uncommitted changes before switching
    if not verify_clean():
        raise WorkspaceError(
            "wolfssl repo has uncommitted changes. "
            "Stash or commit them before running evals."
        )

    original_ref = get_current_ref()

    # Get the first parent of the merge commit (the base branch state)
    try:
        base_commit = _git(["rev-parse", f"{merge_commit}~1"])
    except WorkspaceError:
        raise WorkspaceError(
            f"Cannot find parent of merge commit {merge_commit[:12]}. "
            "Is the wolfssl repo up to date? Run fetch_origin() first."
        )

    logger.info(
        "Checking out pre-PR state: %s (parent of %s)",
        base_commit[:12], merge_commit[:12],
    )
    _git(["checkout", "--detach", base_commit])

    return {
        "original_ref": original_ref,
        "base_commit": base_commit,
        "merge_commit": merge_commit,
    }


def teardown_workspace(context: dict) -> None:
    """Restore the wolfssl repo to its original state.

    The eval claude -p may have modified files (it has write access).
    We discard any changes before checking out the original ref.
    """
    original_ref = context.get("original_ref")
    if not original_ref:
        logger.warning("No original_ref in context, skipping teardown")
        return

    # Discard any modifications left by the eval run
    try:
        _git(["checkout", "--", "."])
        _git(["clean", "-fd"])
    except WorkspaceError as e:
        logger.warning("Failed to clean workspace: %s", e)

    logger.info("Restoring wolfssl repo to %s", original_ref)
    try:
        _git(["checkout", original_ref])
    except WorkspaceError as e:
        logger.error("Failed to restore repo: %s", e)
        for branch in ("master", "main"):
            try:
                _git(["checkout", branch])
                logger.info("Fell back to %s", branch)
                return
            except WorkspaceError:
                continue
        raise


def verify_clean() -> bool:
    """Verify no files were modified during an eval run."""
    status = _git(["status", "--porcelain"])
    if status:
        logger.warning("Unexpected modifications after eval:\n%s", status[:500])
        return False
    return True

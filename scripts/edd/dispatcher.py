from __future__ import annotations

"""HTTP client for the wolfDen eval server.

Dispatches eval runs and returns parsed results.
"""

import json
import logging
import socket
import urllib.error
import urllib.request

from . import EVAL_SERVER_URL

logger = logging.getLogger(__name__)

# Timeout for the HTTP request itself (buffer over eval timeout)
_HTTP_TIMEOUT = 3000  # 50 minutes (buffer over eval timeout)


class EvalError(Exception):
    """Eval dispatch failed."""


class EvalTimeoutError(EvalError):
    """Eval timed out."""


def dispatch_eval(
    prompt: str,
    mode: str = "wolfden",
    model: str = "opus",
    max_turns: int = 500,
    max_budget_usd: float = 50.0,
    timeout: int = 2400,
) -> dict:
    """Dispatch an eval run to the eval server.

    Args:
        prompt: The task prompt
        mode: "wolfden" or "bare"
        model: Claude model to use
        max_turns: Max agentic turns
        max_budget_usd: Cost cap
        timeout: Eval timeout in seconds

    Returns:
        Parsed response dict with response, usage, duration_s fields.

    Raises:
        EvalError: On dispatch failure
        EvalTimeoutError: On timeout
    """
    payload = json.dumps({
        "prompt": prompt,
        "mode": mode,
        "model": model,
        "max_turns": max_turns,
        "max_budget_usd": max_budget_usd,
        "timeout": timeout,
    }).encode()

    url = f"{EVAL_SERVER_URL}/eval"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    logger.info("Dispatching %s eval (model=%s)...", mode, model)

    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            raw = resp.read().decode()
    except socket.timeout as e:
        raise EvalTimeoutError("Eval server request timed out") from e
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise EvalError(f"Eval server HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise EvalError(f"Failed to reach eval server: {e}") from e

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise EvalError(f"Invalid JSON from eval server: {str(e)[:200]}") from e

    # Check for eval-level errors
    if result.get("error"):
        raise EvalError(f"Eval failed: {result['error']}")

    return result


def check_server_health() -> bool:
    """Check if the eval server is running."""
    url = f"{EVAL_SERVER_URL}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("status") == "ok"
    except Exception:
        return False

from __future__ import annotations

"""Shared LLM utilities for EDD analysis and improvement."""

import json
import logging
import re
import subprocess

logger = logging.getLogger(__name__)

CLAUDE_TIMEOUT = 600  # 10 minutes


def call_claude(prompt: str, model: str = "opus", timeout: int = CLAUDE_TIMEOUT) -> str:
    """Call claude -p and return raw output."""
    cmd = ["claude", "-p", "--model", model, "--output-format", "text"]
    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude -p timed out after {timeout}s")
    if result.returncode != 0:
        stderr = result.stderr.strip()[:500]
        raise RuntimeError(f"claude -p failed (rc={result.returncode}): {stderr}")
    return result.stdout.strip()


def _extract_json_object(text: str) -> dict | None:
    """Try to extract a JSON object from text that may contain prose."""
    # Try to find JSON between ```json ... ``` fences
    fence_match = re.search(r'```(?:json)?\s*\n(\{.*?\})\s*\n```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find the first { ... } that parses as valid JSON
    # Use brace depth tracking to find the right closing brace
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    # Keep searching
                    start = text.find('{', i + 1)
                    if start == -1:
                        return None
                    depth = 0

    return None


def parse_json_response(raw: str) -> dict:
    """Parse JSON from claude output, stripping markdown fences.

    Raises ValueError with context on parse failure.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extraction from mixed prose + JSON
    extracted = _extract_json_object(raw)
    if extracted is not None:
        return extracted

    snippet = text[:300] if len(text) > 300 else text
    raise ValueError(
        f"Failed to parse JSON from claude output: no valid JSON found\nSnippet: {snippet}"
    )


def call_claude_json(
    prompt: str,
    model: str = "opus",
    timeout: int = CLAUDE_TIMEOUT,
    max_retries: int = 3,
) -> dict:
    """Call claude -p and parse JSON response, with retries."""
    last_error = None
    for attempt in range(max_retries):
        if attempt == 0:
            actual_prompt = prompt
        else:
            actual_prompt = (
                prompt
                + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Respond with ONLY a JSON object, no other text before or after it."
            )
            logger.warning(
                "Retry %d/%d for JSON parsing...", attempt, max_retries - 1,
            )

        try:
            raw = call_claude(actual_prompt, model=model, timeout=timeout)
            return parse_json_response(raw)
        except ValueError as e:
            last_error = e
            logger.warning("Parse attempt %d failed: %s", attempt + 1, e)
            continue

    raise RuntimeError(
        f"Failed to get valid JSON after {max_retries} attempts: {last_error}"
    )

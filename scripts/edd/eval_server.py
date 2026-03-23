"""Mini FastAPI server wrapping claude -p calls for wolfDen eval dispatch.

Runs as a background process. The orchestrator (Claude Code) hits it via HTTP
to dispatch eval runs without invoking itself recursively.

Usage:
    python -m scripts.edd.eval_server              # port 8200
    python -m scripts.edd.eval_server --port 8201  # custom port
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import SCAFFOLD_DIR, WOLFSSL_REPO, EVAL_SERVER_PORT

logger = logging.getLogger(__name__)

app = FastAPI(title="wolfDen Eval Server", version="0.1.0")


class EvalRequest(BaseModel):
    prompt: str = Field(..., description="The task prompt to send to Claude")
    mode: str = Field("wolfden", description="'wolfden' (with knowledge) or 'bare' (vanilla Claude Code)")
    model: str = Field("sonnet", description="Claude model to use")
    max_turns: int = Field(50, description="Max agentic loop turns")
    max_budget_usd: float = Field(2.0, description="Cost cap per eval run")
    timeout: int = Field(600, description="Timeout in seconds")


class EvalResponse(BaseModel):
    response: str = Field("", description="Claude's text response")
    usage: dict = Field(default_factory=dict, description="Token usage and cost")
    duration_s: float = Field(0, description="Wall clock duration")
    error: str | None = Field(None, description="Error message if eval failed")


@app.post("/eval", response_model=EvalResponse)
async def run_eval(request: EvalRequest) -> EvalResponse:
    """Dispatch a claude -p eval run."""
    # Choose working directory based on mode
    if request.mode == "wolfden":
        cwd = SCAFFOLD_DIR
    elif request.mode == "bare":
        cwd = WOLFSSL_REPO
    else:
        return EvalResponse(error=f"Unknown mode: {request.mode}")

    cmd = [
        "claude", "-p",
        "--model", request.model,
        "--output-format", "json",
        "--max-turns", str(request.max_turns),
    ]

    logger.info(
        "Dispatching %s eval (model=%s, max_turns=%d, budget=$%.2f)...",
        request.mode, request.model, request.max_turns, request.max_budget_usd,
    )
    start = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=request.prompt.encode()),
                timeout=request.timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            duration = time.time() - start
            logger.error("Eval timed out after %.0fs", duration)
            return EvalResponse(
                duration_s=duration,
                error=f"Eval timed out after {request.timeout}s",
            )
    except FileNotFoundError:
        return EvalResponse(
            duration_s=time.time() - start,
            error="claude CLI not found. Is it installed and on PATH?",
        )

    duration = time.time() - start
    returncode = proc.returncode

    if returncode != 0:
        stderr_text = stderr.decode(errors="replace").strip()[:1000]
        logger.error("claude -p failed (rc=%d): %s", returncode, stderr_text)
        return EvalResponse(
            duration_s=duration,
            error=f"claude -p failed (rc={returncode}): {stderr_text}",
        )

    # Parse JSON output from claude -p
    raw = stdout.decode(errors="replace").strip()
    if not raw:
        return EvalResponse(
            duration_s=duration,
            error="Empty output from claude -p",
        )

    try:
        output = json.loads(raw)
    except json.JSONDecodeError as e:
        # claude -p may emit non-JSON on stderr with JSON on stdout
        # Try to find JSON in the output
        logger.warning("Failed to parse full output as JSON: %s", e)
        return EvalResponse(
            response=raw[:5000],
            duration_s=duration,
            error=f"Output was not valid JSON: {str(e)[:200]}",
        )

    # Extract fields from claude -p JSON output
    # 'result' is the final text response; may be empty if Claude hit turn limit
    response_text = output.get("result", "") or ""

    # If result is empty, try to extract text from conversation messages
    if not response_text:
        # Try subresults / messages for the last assistant text block
        for msg in reversed(output.get("messages", [])):
            if msg.get("role") == "assistant":
                # Could be a list of content blocks or a string
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    response_text = content.strip()
                    break
                elif isinstance(content, list):
                    texts = [b.get("text", "") for b in content if b.get("type") == "text"]
                    joined = "\n".join(t for t in texts if t.strip())
                    if joined:
                        response_text = joined
                        break

    if not response_text and output.get("stop_reason") == "max_turns":
        response_text = "[Claude reached max turns without producing a final text response. The investigation was in progress when the turn limit was hit.]"
    usage = {}
    if "usage" in output:
        usage = output["usage"]
    elif "cost_usd" in output:
        usage = {"cost_usd": output["cost_usd"]}

    # Include tool usage stats if available
    if "num_turns" in output:
        usage["num_turns"] = output["num_turns"]

    logger.info(
        "Eval completed in %.0fs (mode=%s, turns=%s)",
        duration, request.mode, usage.get("num_turns", "?"),
    )

    return EvalResponse(
        response=response_text,
        usage=usage,
        duration_s=duration,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    parser = argparse.ArgumentParser(description="wolfDen Eval Server")
    parser.add_argument("--port", type=int, default=EVAL_SERVER_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

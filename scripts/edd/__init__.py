"""Eval-Driven Development (EDD) loop for wolfDen."""

from pathlib import Path

# Repo root: __init__.py -> edd/ -> scripts/ -> repo root
WOLFDEN_DIR = str(Path(__file__).parent.parent.parent)
SCAFFOLD_DIR = f"{WOLFDEN_DIR}/scaffold"
WOLFSSL_REPO = f"{SCAFFOLD_DIR}/repos/wolfssl"
STATE_FILE = f"{WOLFDEN_DIR}/edd-state.json"
REPORTS_DIR = f"{WOLFDEN_DIR}/edd-reports"
PROMPTS_DIR = str(Path(__file__).parent / "prompts")
EVAL_SERVER_PORT = 8200
EVAL_SERVER_URL = f"http://localhost:{EVAL_SERVER_PORT}"

# mywolfden

AI-enhanced development environment for wolfSSL, with an automated
Eval-Driven Development (EDD) loop that continuously improves the
knowledge base.

## Two Components

### 1. Scaffold (the development environment)

`scaffold/` is a portable Claude Code workspace. Clone this repo, run
`setup.sh` to pull the wolfSSL repos you work on, then launch `claude` —
it automatically loads 150+ domain knowledge files covering wolfSSL
architecture, build system, platforms, integrations, and crypto patterns.

```bash
cd scaffold
./setup.sh          # Select and clone wolfSSL repos
claude              # Claude now knows wolfSSL
```

See [scaffold/README.md](scaffold/README.md) for details.

### 2. EDD Loop (the automation)

`scripts/edd/` implements an automated evaluation loop that:
- Selects merged PRs from wolfssl/wolfssl
- Runs "bare Claude" (no knowledge) and "wolfDen Claude" (with knowledge)
  against the same PR
- Analyzes differences to identify knowledge gaps
- Proposes and applies improvements to `.claude/rules/` files
- Re-evaluates to measure impact (improved/regressed/neutral)

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (`claude`)
- [GitHub CLI](https://cli.github.com/) (`gh`) — authenticated
- Python 3.12+
- `pip install -r requirements.txt`

## Running the EDD Loop

```bash
# Start the eval server (required — dispatches claude -p calls)
python -m scripts.edd.eval_server &

# Run a single iteration
python -m scripts.edd --iterations 1

# Evaluate a specific PR
python -m scripts.edd --pr 9800

# Dry run (show what would happen)
python -m scripts.edd --dry-run

# Overnight autonomous loop (up to 20 PRs)
./run_edd_loop.sh
```

Reports are written to `edd-reports/`. State is tracked in `edd-state.json`
(delete it to start fresh).

## Knowledge Sync

`sync_knowledge.py` pulls knowledge from the wolfssl-llm-bots support
knowledge base and reframes it for developer context. Requires access to
the source knowledge directory:

```bash
# Via CLI argument
python sync_knowledge.py --source /path/to/wolfssl-llm-bots/apps/support-knowledge/knowledge

# Via environment variable
export WOLFDEN_KNOWLEDGE_SOURCE=/path/to/knowledge
python sync_knowledge.py

# Dry run
python sync_knowledge.py --source /path/to/knowledge --dry-run
```

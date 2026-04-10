# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

wolfDen is a portable Claude Code workspace for wolfSSL development. When you
run `claude` inside `scaffold/`, it automatically loads domain knowledge
covering wolfSSL architecture, conventions, common task checklists, and scope
boundaries — so Claude understands wolfSSL patterns without you having to
explain them.

## Quick Start

```bash
cd scaffold
./setup.sh          # Select and clone the wolfSSL repos you work on
claude              # Claude now knows wolfSSL
```

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI (`claude`)
- [GitHub CLI](https://cli.github.com/) (`gh`) — authenticated

## Knowledge Architecture

Knowledge is organized in tiers for efficient context loading:

```
scaffold/.claude/rules/
├── conventions.md      # Always loaded — coding style, memory patterns, build system
├── discipline.md       # Always loaded — verification mandates
├── scope-map.md        # Always loaded — companion-file relationships
├── checklists/         # On-demand — task-type checklists (add flag, add API, etc.)
├── boundaries/         # On-demand — scope disambiguation (OpenSSL compat, TLS versions)
└── naming/             # On-demand — macro prefixes, PQC naming conventions
```

**Root-level rules** load in every conversation — these encode the conventions
and discipline that apply universally.

**Subdirectory rules** load on-demand when Claude is working in relevant areas.
This keeps context focused: you get the ESP32 checklist when working on ESP32,
not when debugging a certificate parser.

## Updating Knowledge

Pull this repo to get the latest knowledge files:

```bash
git pull
```

To contribute improvements, edit files in `scaffold/.claude/rules/` and submit a PR.

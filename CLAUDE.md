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
scaffold/
├── .claude/rules/                  # T1 + T2 (auto-loaded)
│   ├── conventions.md              # T1 — always loaded: coding style, memory, build
│   ├── discipline.md               # T1 — always loaded: verification mandates
│   ├── scope-map.md                # T1 — always loaded: companion-file relationships
│   ├── checklists/                 # T2 — glob-triggered: task-type checklists
│   ├── boundaries/                 # T2 — glob-triggered: scope disambiguation
│   └── naming/                     # T2 — glob-triggered: macro prefixes, PQC naming
├── knowledge/                      # T3 — cold storage, never auto-loaded
│   ├── index.md                    # Routing table (included via @ in CLAUDE.md)
│   ├── crypto/                     # Side channels, FIPS, TLS errors, PQ, SP math
│   ├── platforms/                  # ESP32, STM32, FreeRTOS, Zephyr, Linux KM
│   ├── integrations/               # curl, OpenSSH, configure deps
│   ├── products/                   # wolfTPM, wolfBoot, DO-178C
│   ├── security/                   # CWE patterns, attack principles
│   └── implementation/             # I/O callbacks, HW acceleration
```

**T1 (always loaded)** — conventions and discipline that apply universally.

**T2 (glob-triggered)** — loads when Claude is working in relevant file areas.

**T3 (cold, on-demand)** — deep domain knowledge that Claude reads only when
a task matches the "Read When" trigger in the index. This keeps context lean
while making ~1,770 lines of domain expertise available when needed.

## Updating Knowledge

Pull this repo to get the latest knowledge files:

```bash
git pull
```

To contribute improvements, edit files in `scaffold/.claude/rules/` or
`scaffold/knowledge/` and submit a PR.

# wolfDen

AI-enhanced development environment for wolfSSL products. When you use
Claude Code in this workspace, Claude automatically has deep knowledge
of wolfSSL architecture, build system, debugging patterns, and all
wolfSSL product APIs.

## Quick Start

```bash
git clone git@github.com:ColtonWilley/mywolfden.git
cd mywolfden/scaffold
./setup.sh          # Select and clone the wolfSSL repos you work on
claude              # Claude now knows wolfSSL
```

## How It Works

- `.claude/rules/` contains domain knowledge that Claude loads automatically
- Some rules load for every conversation (architecture, build system, error codes)
- Most rules load on-demand when Claude reads files matching specific patterns
  (e.g., ESP32 knowledge loads when you work on ESP-IDF code)
- A session hook scans `repos/` and tells Claude what you have checked out

You don't need to do anything special. Just write your normal prompts —
Claude handles the rest.

## Adding Repos

Run `setup.sh` again, or clone manually:

```bash
git clone git@github.com:wolfssl/wolfssl.git repos/wolfssl
```

The next Claude session will detect it automatically.

## Updating Knowledge

Pull this repo to get the latest knowledge files:

```bash
git pull
```

To contribute improvements, edit files in `.claude/rules/` and submit a PR.

# wolfDen

AI-enhanced development environment for wolfSSL. Run Claude Code inside
this workspace and it automatically understands wolfSSL architecture,
conventions, and common development tasks.

## Quick Start

```bash
git clone git@github.com:wolfSSL/wolfden.git
cd wolfden/scaffold
./setup.sh          # Select and clone the wolfSSL repos you work on
claude              # Claude now knows wolfSSL
```

## What You Get

Claude automatically loads domain knowledge covering:

- **Coding conventions** — 4-space indent, `XMALLOC`/`XFREE` patterns,
  `ForceZero` for secrets, error code chains, macro registration
- **Verification discipline** — Never claim infrastructure exists without
  grepping, follow the code over loaded knowledge, check for applicable
  checklists before scoping work
- **Scope maps** — Which files change together (error codes → error strings,
  configure flags → CMake, new algorithms → test registration)
- **Task checklists** — Step-by-step for common tasks: adding configure flags,
  crypto callbacks, error codes, hardware acceleration, PKCS#11 algorithms,
  public APIs, TLS named groups, Linux kernel module changes
- **Boundary disambiguation** — OpenSSL compat dual paths, PKCS#11 vs CryptoCb,
  test system conventions, TLS version code paths
- **Naming conventions** — Macro prefixes, post-quantum naming patterns

## How It Works

- Root-level rules (`conventions.md`, `discipline.md`, `scope-map.md`) load
  in every conversation
- Subdirectory rules (`checklists/`, `boundaries/`, `naming/`) load on-demand
  when Claude is working in relevant areas
- A session hook scans `repos/` to tell Claude what you have checked out

You don't need to do anything special — just write your normal prompts.

## Adding Repos

Run `setup.sh` again, or clone manually:

```bash
git clone git@github.com:wolfssl/wolfssl.git repos/wolfssl
```

The next Claude session will detect it automatically.

## Contributing Knowledge

Edit files in `scaffold/.claude/rules/` and submit a PR. See the existing
files for format and style.

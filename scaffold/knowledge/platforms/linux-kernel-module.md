# Linux Kernel Module (linuxkm)

> One-line summary: wolfSSL's kernel-space build constraints, linuxkm zone architecture, and LKCAPI integration patterns.

**When to read**: building wolfSSL as a Linux kernel module, integrating with LKCAPI, debugging linuxkm zone visibility issues, or working on kernel-space TLS/WireGuard crypto.

---

## Core Define

| Define | Purpose |
|--------|---------|
| `WOLFSSL_LINUXKM` | Enables all kernel-module adaptations (no libc, kmalloc, kernel headers) |

## No-libc Constraints

In kernel space there is no libc. wolfSSL maps its abstractions to kernel equivalents:

| wolfSSL Macro | Kernel Equivalent |
|---------------|-------------------|
| `XMALLOC(s,h,t)` | `kmalloc(s, GFP_KERNEL)` |
| `XFREE(p,h,t)` | `kfree(p)` |
| `XREALLOC(p,n,h,t)` | `krealloc(p, n, GFP_KERNEL)` |

No `printf`, no `fopen`, no `time()` -- all must use kernel equivalents (`printk`, kernel file ops, `ktime_get_real_seconds`).

## Build

Built from `linuxkm/` directory: `make -C linuxkm`. This is entirely separate from the standard `./configure && make` userspace build.

## linuxkm_wc_port.h Zone Architecture

`linuxkm/linuxkm_wc_port.h` has distinct macro visibility zones gated by `#ifdef BUILDING_WOLFSSL`. Moving a define between zones changes who can see it:

| Zone | Visibility | Contents |
|------|-----------|----------|
| **Pre-guard** (before `#ifdef BUILDING_WOLFSSL`) | ALL consumers (internal + external) | Public API declarations, entropy framework setup, extern function decls |
| **BUILDING_WOLFSSL** | wolfSSL compilation units only | Kernel header includes, LKCAPI registration macros, internal function pointers |
| **!BUILDING_WOLFSSL** | External callers only | Minimal API surface (e.g., vector register save/restore) |
| **Post-guard** (after both guards) | Everyone | Mutex/spinlock selection, FIPS name mappings |

**Example**: `LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT` is in the BUILDING_WOLFSSL zone so `random.c` can gate out `get_random_bytes()` calls that would recurse when wolfCrypt IS the kernel's default RNG. Moving it to pre-guard would leak it to external consumers.

## LKCAPI Integration

### Macro Gate Chain

LKCAPI registration uses cascading macros:

```
LINUXKM_LKCAPI_REGISTER_ALL
  -> enables individual algorithm registrations
  -> each suppressible via LINUXKM_LKCAPI_DONT_REGISTER_<algo>
```

Follow the chain in `linuxkm_wc_port.h`'s BUILDING_WOLFSSL zone to trace why an algorithm is/isn't registered.

### Handle-Based API Convention

Kernel-facing LKCAPI functions receive explicit kernel crypto handles, NOT wolfCrypt globals:

- Handle types: `struct crypto_rng *`, `struct crypto_shash *`, etc.
- Extract wolfCrypt state: `crypto_rng_ctx(tfm)` to get private context
- Validate ownership: compare `tfm->base.__crt_alg->cra_init` against wolfCrypt's init function pointer
- **Never** access global wolfCrypt RNG state from LKCAPI callbacks

This pattern is consistent across `lkcapi_glue.c` and `lkcapi_sha_glue.c`. All new kernel-facing functions must follow it.

## Key Files

| File | Purpose |
|------|---------|
| `linuxkm/linuxkm_wc_port.h` | Zone architecture, LKCAPI macro gates, platform defines |
| `linuxkm/lkcapi_glue.c` | LKCAPI cipher/RNG registration glue |
| `linuxkm/lkcapi_sha_glue.c` | LKCAPI hash algorithm registration |
| `linuxkm/module_hooks.c` | `module_init` / `module_exit` entry points |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| Infinite recursion in `get_random_bytes()` | wolfCrypt registered as default RNG but calls `get_random_bytes()` internally | Check `LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT` gating in `random.c` |
| Undefined symbol at module load | Function in wrong zone of `linuxkm_wc_port.h` | Move define to correct visibility zone |
| Kernel panic during crypto operation | LKCAPI callback accessing global state instead of handle context | Use `crypto_*_ctx(tfm)` pattern, not globals |
| Build failure with missing headers | Kernel headers not matching running kernel | Ensure `/lib/modules/$(uname -r)/build` exists and matches |
| LKCAPI algorithm not registering | Suppression macro set or umbrella macro missing | Trace the `REGISTER_ALL` -> `DONT_REGISTER_<algo>` chain |

## What This File Does NOT Cover

Standard Linux userspace build (`./configure && make`), cross-compilation for Linux userspace, general kernel module development education. See `embedded-common.md` only if also targeting an embedded Linux variant.

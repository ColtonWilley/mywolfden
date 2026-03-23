---
paths:
  - "**/meta-*/**"
  - "repos/meta-wolfssl/**"
---

# OpenEmbedded Core (Yocto) — External Platform Summary

## Current State
OpenEmbedded-core (OE-core) is the base layer for Yocto Project builds. It provides core recipes including the default OpenSSL recipe (`meta/recipes-connectivity/openssl/`). wolfSSL integrates via the separate `meta-wolfssl` layer which provides recipe files and `PREFERRED_PROVIDER` overrides.

## Architecture
- **Layer system**: Yocto uses layers (`meta-*` directories) stacked via `bblayers.conf`. OE-core provides `virtual/ssl` which defaults to OpenSSL.
- **Recipe files**: `.bb` files define how to fetch, configure, compile, and install packages. `.bbappend` files in higher-priority layers modify existing recipes.
- **Virtual providers**: `PREFERRED_PROVIDER_virtual/ssl` mechanism allows swapping OpenSSL for wolfSSL system-wide.

## wolfSSL Integration Notes
- `meta-wolfssl` layer provides `wolfssl_%.bb` recipe and sets `PREFERRED_PROVIDER_virtual/ssl = "wolfssl"`.
- Adding the layer: clone `meta-wolfssl` into your Yocto build, add to `bblayers.conf`, set `PREFERRED_PROVIDER` in `local.conf`.
- The wolfSSL recipe builds with `--enable-opensslextra --enable-opensslall` to provide the OpenSSL compat layer that downstream recipes expect.
- Packages depending on `virtual/ssl` (curl, openssh, etc.) automatically link against wolfSSL instead of OpenSSL.
- FIPS: `meta-wolfssl` can include the FIPS-validated wolfSSL build. Set `WOLFSSL_FIPS = "1"` in recipe or `local.conf`.
- Common issue: Some OE-core recipes hard-code `openssl` as a dependency instead of using `virtual/ssl`. These need `.bbappend` files to fix the dependency.
- Linux kernel module (`wolfssl-linuxkm`): meta-wolfssl can also provide the kernel module recipe for in-kernel TLS.
- Cross-compilation: Yocto handles cross-compile toolchains automatically. wolfSSL's autoconf build works well with Yocto's cross-compile environment.

## Key Files (in OE-core)
- `meta/recipes-connectivity/openssl/` — Default OpenSSL recipes (what wolfSSL replaces)
- `meta/classes/` — Build classes including SSL-related helpers
- `meta/conf/bitbake.conf` — Default `PREFERRED_PROVIDER` settings

## Key Files (in meta-wolfssl)
- `recipes-wolfssl/wolfssl/wolfssl_%.bb` — Main wolfSSL recipe
- `recipes-wolfssl/wolfssl/wolfssl_%.bbappend` — Recipe modifications
- `conf/layer.conf` — Layer configuration and priority

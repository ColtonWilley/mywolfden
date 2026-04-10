---
paths:
  - "**/linuxkm/**"
  - "**/Kbuild"
---

# Linux Kernel Module (linuxkm) Changes

## When This Applies
Any change touching the linuxkm subsystem — build targets, source files,
kernel-specific features, or module configuration.

## Four-File Coordination

These four files must stay in sync:

1. **`linuxkm/Makefile`** — Module build targets, `LIBWOLFSSL_NAME`, hash
   generation rules, environment variable consumption.

2. **`linuxkm/Kbuild`** — Kernel build counterpart: `obj-m`, module
   target names, `.mod.o` rules, symbol export/namespace settings. Must
   mirror naming variables from Makefile.
   VERIFY: compare target names between Makefile and Kbuild.

3. **`Makefile.am`** — Forwarding rules (`+$(MAKE) -C linuxkm <target>`)
   for any linuxkm target accessible from project root. Environment
   variable passthrough list must include any new `AC_SUBST` variables.
   VERIFY: grep for existing linuxkm targets in Makefile.am.

4. **`configure.ac`** — Kernel-specific `--enable-kernel-*` options
   follow standard `AC_ARG_ENABLE` + `AM_CFLAGS` + `AC_SUBST` pattern.

Also: **`linuxkm/include.am`** must list new source files for automake.

## Scope Boundaries

- linuxkm has a uniquely complex multi-file build pipeline. Do not assume
  changes to one file are sufficient — verify all four are consistent.

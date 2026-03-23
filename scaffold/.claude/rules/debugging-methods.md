---
paths:
  - "**/port/**"
  - "**/IDE/**"
  - "**/callbacks*"
  - "**/sniffer*"
  - "**/dtls*"
  - "**/internal.c"
  - "**/random.c"
  - "**/*.S"
  - "**/*.s"
  - "**/sp_*.c"
  - "**/user_settings*"
---

# wolfSSL Specialized Debugging Methods

These paradigms load contextually when working with relevant code. For core
investigation essentials (evidence discipline, gate findings, differential
diagnosis), see investigation-methods.md.

## Hardware Port Debugging

When investigating hardware-specific errors (WC_HW_E, crypto accelerator):

- Find ALL return sites for the error code in the port file
- **Trace the algorithm/mode selection function completely** — every branch,
  not just error paths. Identify which enum value gets selected, then ask:
  does the hardware actually support that value?
- **Trace what gets SENT to the hardware, not just where errors are caught.**
  The error comes FROM the hardware because the port code made a bad
  selection. Follow: wolfSSL API -> port selection logic -> hardware API call.

## State Machine Debugging

wolfSSL uses state machines extensively (TLS handshake, DTLS retransmit,
non-blocking I/O). When debugging state-dependent behavior:

- **Trace callee state behavior.** (See investigation-methods.md for the
  general principle.) For state machines: read the callee at the CURRENT
  STATE, not just its entry point — behavior depends on which case executes.
- **Non-blocking: trace TWO calls.** The first call usually works. The bug
  is in what happens on re-entry after I/O completes.
- **Check symmetric paths.** If a bug exists in accept, check connect.

## Cross-Platform Integration

When debugging cross-platform or cross-ABI issues:

- The bug is often in the INTEGRATION MECHANISM, not in either side's code.
- **Check BOTH call directions**: consumer -> wolfSSL AND wolfSSL -> consumer
  (callbacks). If only one direction has correct calling convention wrapping,
  the other will pass garbage parameters.
- Check struct layout: `long` is 8 bytes in LP64 but 4 bytes in LLP64.

## Bug Investigation

When investigating a reported code defect:

- **Verify the claim against actual code.** Read the function first.
- **Reachability analysis.** Grep for all call sites. For each caller,
  determine if the buggy condition can actually be triggered.
- **Same-class audit.** When you confirm a pattern, check for it in
  symmetric functions and adjacent code.

## Custom Implementations

When a custom callback is configured (CUSTOM_RAND_GENERATE, WOLFSSL_USER_IO,
crypto callbacks):

- The custom implementation IS the code that runs. Trace it first.
- **Responsibility transfer.** When custom callbacks are registered, the
  library's built-in management may become inactive.

## Dependency Chain Verification

When disabling an algorithm (`NO_X`, `--disable-X`):

- **Trace what enabled protocols depend on it.** Protocol versions have
  mandatory algorithm requirements.
- **Common trap:** disabling a "legacy" algorithm that an enabled protocol
  version still requires internally.

## ISA-Aware Optimization

When targeting a specific CPU architecture:

- Check for `WOLFSSL_SP_` ISA-specific assembly flags: `X86_64`, `ARM64`,
  `ARM32`, `ARM_THUMB`, `ARM_CORTEX_M_ASM`, `RISCV32`, `RISCV64`.
- Verify ISA extensions match (NEON, AES-NI, RISC-V M extension).

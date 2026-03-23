# Bare Claude Response — PR #9935

All changes look correct. Here's a summary of what was implemented:

## Changes

### New API: `wolfSSL_check_ip_address(WOLFSSL* ssl, const char* ip)`

Mirrors `wolfSSL_check_domain_name()` but checks IP addresses against SAN IP entries in the peer certificate. Requires `WOLFSSL_IP_ALT_NAME` to be defined (enabled by `--enable-ip-alt-name` or `--enable-opensslextra`).

### Files modified:

1. **`wolfssl/ssl.h`** — Declaration with `WOLFSSL_ABI WOLFSSL_API`, guarded by `WOLFSSL_IP_ALT_NAME`
2. **`wolfssl/internal.h`** — Added `ipAddr` buffer field to `Buffers` struct, guarded by `WOLFSSL_IP_ALT_NAME`
3. **`src/ssl.c`** — Implementation that stores the IP string in `ssl->buffers.ipAddr` (same pattern as `wolfSSL_check_domain_name()` with `domainName`)
4. **`src/internal.c`** — Two changes:
   - **Certificate verification** (~line 16905): After the domain name check, added IP address check using `CheckIPAddr()` against `ssl->buffers.ipAddr`, returning `IPADDR_MISMATCH` on failure
   - **`wolfSSL_ResourceFree()`** (~line 8724): Cleanup of `ssl->buffers.ipAddr.buffer`
5. **`tests/api.c`** — Unit test `test_wolfSSL_check_ip_address_basic` that verifies:
   - Mismatch fails (cert has `127.0.0.1`, test uses `192.168.1.1`)
   - Match succeeds (cert has `127.0.0.1`, test uses `127.0.0.1`)
6. **`doc/dox_comments/header_files/ssl.h`** — English doxygen documentation
7. **`doc/dox_comments/header_files-ja/ssl.h`** — Japanese doxygen documentation

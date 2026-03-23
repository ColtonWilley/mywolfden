# wolfDen Claude Response (iter1) — PR #9935

All changes look correct. Here's a summary of what was implemented:

## Changes Made

**7 files modified, ~203 insertions, 1 fix:**

### `wolfssl/ssl.h` — Public API declaration
- Added `wolfSSL_check_ip_address(WOLFSSL* ssl, const char* ipaddr)` with `WOLFSSL_ABI WOLFSSL_API` markers, mirroring `wolfSSL_check_domain_name()`

### `wolfssl/internal.h` — Buffer storage
- Added `buffer ipasc;` field in the `Buffers` struct (next to `domainName`)

### `src/ssl.c` — Implementation
- Added `wolfSSL_check_ip_address()` following the exact pattern of `wolfSSL_check_domain_name()`: validate args, free existing buffer, allocate+copy, null-terminate

### `src/internal.c` — Verification + cleanup
1. **Cleanup**: Added `XFREE(ssl->buffers.ipasc.buffer, ...)` in `wolfSSL_ResourceFree()` next to the `domainName` cleanup
2. **Bug fix**: Fixed missing 6th argument (`isIP=0`) in `CheckForAltNames()` call in the `WOLFSSL_ALLOW_NO_CN_IN_SAN` code path
3. **Verification**: Added `#ifndef OPENSSL_EXTRA` IP address check in `ProcessPeerCerts()` that calls `CheckIPAddr()` against `ssl->buffers.ipasc.buffer`, returning `IPADDR_MISMATCH` on failure. Gated by `#ifndef OPENSSL_EXTRA` because the OPENSSL_EXTRA path already handles IP checks via `ssl->param->ipasc` in `DoVerifyCallback()`

### `doc/dox_comments/header_files/ssl.h` + `header_files-ja/ssl.h` — Doxygen
- Added English and Japanese documentation for `wolfSSL_check_ip_address()`

### `tests/api.c` — Unit tests
- **`test_wolfSSL_check_ip_param_basic`**: Tests the OPENSSL_EXTRA path (`X509_VERIFY_PARAM_set1_ip_asc`), verifying mismatch failure and 127.0.0.1 success against the test cert's SAN
- **`test_wolfSSL_check_ip_address_basic`**: Tests the native path (`wolfSSL_check_ip_address`), same mismatch/match pattern
- Both have appropriate `#ifdef` guards and stub fallbacks

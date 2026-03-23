# wolfDen Claude Response (baseline) — PR #9935

The feature is **already fully implemented** in the current codebase. Here's what exists:

1. **Declaration** (`ssl.h:3359-3362`): `wolfSSL_check_ip_address()` declared with `WOLFSSL_ABI WOLFSSL_API`, gated by `WOLFSSL_IP_ALT_NAME`
2. **Implementation** (`ssl.c:7566-7597`): Mirrors `wolfSSL_check_domain_name()` exactly — stores IP string in `ssl->buffers.ipAddr`
3. **Struct field** (`internal.h:4894-4896`): `buffer ipAddr` in the `Buffers` struct
4. **Verification path** (`internal.c:16905-16913`): During cert verification, calls `CheckIPAddr()` on the stored IP, returns `IPADDR_MISMATCH` on failure
5. **OPENSSL_EXTRA path** (`internal.c:14836-14843`): Also checks via `ssl->param->ipasc` for the OpenSSL compat layer
6. **Cleanup** (`internal.c:8723-8725`): `ipAddr.buffer` freed in `wolfSSL_ResourceFree()`
7. **Core check** (`internal.c:13486-13491`): `CheckIPAddr()` delegates to `CheckHostName()` with `isIP=1`
8. **Error code** (`error-ssl.h`): `IPADDR_MISMATCH = -325`
9. **Unit tests** (`tests/api.c:16043-16085`): Tests both match (127.0.0.1) and mismatch (192.168.1.1) cases
10. **Configure flag** (`configure.ac`): `--enable-ip-alt-name` sets `WOLFSSL_IP_ALT_NAME`

This feature is complete — the API, verification logic, error handling, cleanup, dual OPENSSL_EXTRA path, and tests are all in place. The commit at HEAD (`82b6b9cb2`) already contains the full implementation for ZD 21313.

Is there something specific about this implementation you'd like me to change or extend? Or were you looking at a different branch/version where this hasn't been merged yet?

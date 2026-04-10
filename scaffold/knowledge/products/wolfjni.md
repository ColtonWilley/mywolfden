# wolfSSL JNI / JSSE Provider

> One-line summary: two-layer Java integration (JNI thin wrapper + JSSE provider), native build dependency, and Android BKS/AOSP patterns.

**When to read**: Integrating wolfSSL into Java/Android apps, debugging UnsatisfiedLinkError, or setting up wolfJSSE as a security provider.

---

## Architecture

- **wolfSSL JNI** (`wolfssl.jar`) — thin wrapper around native C wolfSSL API
- **wolfJSSE** (`wolfssl-jsse.jar`) — JSSE provider for `javax.net.ssl` (SSLSocket, SSLEngine, SSLContext)
- **wolfCrypt JNI/JCE** — separate repo (`wolfcrypt-jni`), wraps wolfCrypt primitives

Most users want wolfJSSE — standard Java TLS code works with wolfSSL underneath.

## Native Dependency

wolfSSL must be compiled with JNI support first:
```bash
cd wolfssl && ./configure --enable-jni && make && sudo make install
```

Windows: add `#define WOLFSSL_JNI` plus `HAVE_EX_DATA`, `OPENSSL_EXTRA`,
`OPENSSL_ALL`, `HAVE_CRL`, `HAVE_OCSP`, `HAVE_ECC`, `HAVE_DH`,
`HAVE_TLS_EXTENSIONS`, `HAVE_SNI`, `HAVE_ALPN`, `KEEP_PEER_CERT`,
`SESSION_CERTS` to `user_settings.h`.

## Provider Registration

```java
import com.wolfssl.provider.jsse.WolfSSLProvider;
Security.insertProviderAt(new WolfSSLProvider(), 1);  // highest priority
```

Supported protocols: `TLSv1.2`, `TLSv1.3`, `DTLSv1.3` (SSLEngine only).

## Android

- **App-level**: example project at `IDE/Android/`. Native wolfSSL source in
  `app/src/main/cpp/wolfssl/`. KeyStore must be BKS format (not JKS) —
  convert with `examples/provider/convert-to-bks.sh`.
- **AOSP system-level**: install wolfJSSE as system JSSE provider.
  Instructions in `platform/android_aosp/`.

## Debug Properties

| Property | What it enables |
|----------|----------------|
| `-Dwolfssl.debug=true` | Native wolfSSL debug (requires `--enable-debug`) |
| `-Dwolfjsse.debug=true` | JSSE provider logging |
| `-Dwolfjsse.debugFormat=JSON` | JSON output for DataDog/tools |

## Known Failure Modes

| Symptom | Root Cause | Key File/Function |
|---------|------------|-------------------|
| `UnsatisfiedLinkError` on startup | `libwolfssl.so` / `libwolfssljni.so` not on library path | Set `LD_LIBRARY_PATH` or `DYLD_LIBRARY_PATH` |
| Missing symbols at JNI load | wolfSSL built without `--enable-jni` | Rebuild with flag |
| `FIPS_NOT_ALLOWED_E` with dual providers | Concurrent CAST on wolfJSSE + wolfJCE threads | Set `wolfjsse.skipFIPSCAST=true`, run CASTs via JCE |
| KeyStore errors on Android | JKS format instead of BKS | Convert with `convert-to-bks.sh` |
| Session resumption not working | Missing system property | Set `jdk.tls.client.enableSessionTicketExtension=true` (Java 13+) |

## What This File Does NOT Cover

- wolfCrypt JNI/JCE (separate repo, separate patterns)
- JSSE API usage (standard Java — use JDK docs)
- Maven/Gradle build details beyond initial setup

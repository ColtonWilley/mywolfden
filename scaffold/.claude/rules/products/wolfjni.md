---
paths:
  - "repos/wolfssljni/**"
  - "**/wolfssljni/**"
  - "**/*.java"
---

# wolfSSL JNI / JSSE Provider Patterns

## Overview
The wolfssljni package provides two layers of Java support for wolfSSL:
- **wolfSSL JNI** — Thin JNI wrapper around the native C wolfSSL API (`wolfssl.jar`)
- **wolfJSSE** — Java Secure Socket Extension provider built on top of the JNI layer (`wolfssl-jsse.jar`)

Most customers use the JSSE provider, which plugs into the standard `javax.net.ssl` API (SSLSocket, SSLEngine, SSLContext, etc.) so existing Java TLS code works with wolfSSL underneath.

**wolfCrypt JNI/JCE is a separate repo** (`wolfcrypt-jni`). That package wraps wolfCrypt cryptographic primitives and registers a JCE provider. This document covers only the wolfssljni/wolfJSSE package.

## Build Dependencies — Native wolfSSL Required
The most common support issue: wolfSSL JNI/JSSE requires native wolfSSL to be compiled and installed first. The native library must be built with JNI support enabled.

### Linux/macOS Build
```
cd wolfssl
./configure --enable-jni
make check
sudo make install

cd wolfssljni
export JUNIT_HOME=/path/to/junit/jars
make build
make check
```

### Windows Build (Visual Studio)
- Build wolfSSL DLL from `wolfssl64.sln` (non-FIPS) or `IDE\WIN10\wolfssl-fips.sln` (FIPS)
- Must add `#define WOLFSSL_JNI` plus other required defines to `user_settings.h`
- Then open `wolfssljni\IDE\WIN\wolfssljni.sln` and build matching configuration
- Required user_settings.h defines: `WOLFSSL_JNI`, `HAVE_EX_DATA`, `OPENSSL_EXTRA`, `OPENSSL_ALL`, `HAVE_CRL`, `HAVE_OCSP`, `HAVE_ECC`, `HAVE_DH`, `HAVE_TLS_EXTENSIONS`, `HAVE_SNI`, `HAVE_ALPN`, `KEEP_PEER_CERT`, `SESSION_CERTS`, plus certificate/key generation defines

### Maven Integration
After building the native JNI shared library (`make native`), use Maven for Java side:
```
mvn compile     # compile Java sources
mvn test        # run JUnit tests
mvn package     # create JAR (target/wolfssl-jsse-X.X.X-SNAPSHOT.jar)
mvn install     # install to local Maven repo (~/.m2/repository/com/wolfssl/wolfssl-jsse/)
```
The native `libwolfssljni.so`/`.dylib` must still be on the library search path (`LD_LIBRARY_PATH` or `DYLD_LIBRARY_PATH`).

## Provider Registration
Applications register wolfJSSE as a security provider at runtime:

```java
import com.wolfssl.provider.jsse.WolfSSLProvider;

// Append as lowest-priority provider:
Security.addProvider(new WolfSSLProvider());

// Or insert as highest-priority provider:
Security.insertProviderAt(new WolfSSLProvider(), 1);
```

Supported SSLContext protocols: `SSL`, `TLS`, `DEFAULT`, `TLSv1`, `TLSv1.1`, `TLSv1.2`, `TLSv1.3`, `DTLSv1.3` (SSLEngine only).

## Android Integration

### Application-Level (Android Studio)
- An example Android Studio project is at `IDE/Android/`
- Native wolfSSL source must be placed at `IDE/Android/app/src/main/cpp/wolfssl/`
- KeyStore files must be converted from JKS to BKS format (`convert-to-bks.sh` script provided)
- BKS files and certs must be pushed to device via `adb push`
- Provider registration is done in application code (same `Security.addProvider()` call)

### AOSP System-Level
wolfJSSE can be installed into Android AOSP as the system-wide JSSE provider, making all apps automatically use wolfSSL for TLS. Instructions in `platform/android_aosp/` directory.

## Common Issues

### UnsatisfiedLinkError on Startup
The native libraries cannot be found. Ensure both `libwolfssl.so` and `libwolfssljni.so` are on the library path. Common fixes:
- Set `LD_LIBRARY_PATH` (Linux) or `DYLD_LIBRARY_PATH` (macOS) to include the library directories
- On Windows, ensure the DLL directories are on `PATH`
- For custom loading, use `wolfssl.skipLibraryLoad=true` system property, then call `System.load()` with explicit paths before `wolfSSL.loadLibrary()`

### wolfSSL Not Compiled with JNI Support
If wolfSSL was built without `--enable-jni`, the JNI layer will fail to link or will be missing required symbols. Rebuild wolfSSL with `--enable-jni` (or `WOLFSSL_JNI` define on Windows).

### FIPS CAST Errors with Dual Providers
When using both wolfJSSE and wolfJCE (from wolfcrypt-jni) with FIPS, concurrent CAST execution on different threads causes `FIPS_NOT_ALLOWED_E`. Fix: set `wolfjsse.skipFIPSCAST=true` before constructing `WolfSSLProvider`, and run CASTs once through wolfJCE's `Fips.runAllCast_fips()`.

### SSLEngine Performance
SSLEngine is used in frameworks like Netty, gRPC, and Android. If throughput is low:
- Update to v1.16.0+ which improved SSLEngine send/receive performance 20-30%
- ByteBuffer pool is enabled by default for avoiding unaligned memory access; tune pool size via `wolfssl.readWriteByteBufferPool.size` security property

### Session Resumption Not Working
- Client session cache is enabled by default; verify it has not been disabled via `wolfjsse.clientSessionCache.disabled=true`
- Session tickets require `jdk.tls.client.enableSessionTicketExtension=true` system property (Java 13+)
- wolfSSL must be compiled with session ticket support

### Certificate Chain Validation Failures
- Cross-signed certificates: fixed in v1.16.0 (PRs 292, 294)
- Chain order issues from `getCerts()`: fixed in v1.16.0 (PRs 282, 289)
- Use `WOLFSSL_ALT_CERT_CHAINS` define in native wolfSSL build

### Android BKS KeyStore Errors
Android requires BKS (Bouncy Castle KeyStore) format, not JKS. Use the provided `examples/provider/convert-to-bks.sh` script with a Bouncy Castle provider JAR to convert.

## Debugging
Enable debug logging via system properties at runtime:

| Property | Description |
| --- | --- |
| `-Dwolfssl.debug=true` | Native wolfSSL debug (requires `--enable-debug` in native build) |
| `-Dwolfjsse.debug=true` | wolfJSSE provider debug logging |
| `-Dwolfssljni.debug=true` | JNI layer debug logging |
| `-Dwolfsslengine.debug=true` | SSLEngine-specific debug logging |
| `-Djavax.net.debug=all` | Standard JDK TLS debug logging |

Debug output can be switched to JSON format for tools like DataDog: `-Dwolfjsse.debugFormat=JSON`.

## Java 9+ Module System (JPMS)
Building with Java 9+ automatically produces a modular JAR (`com.wolfssl` module). This enables `jlink` for creating minimal custom runtimes with wolfJSSE. Java 8 builds produce standard classpath JARs and remain fully supported.

## Key Resources
- Manual: https://www.wolfssl.com/documentation/manuals/wolfssljni/
- Repository: https://github.com/wolfSSL/wolfssljni
- wolfCrypt JCE (separate): https://github.com/wolfSSL/wolfcrypt-jni
- Maven artifact: `com.wolfssl:wolfssl-jsse`

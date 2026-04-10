# Knowledge Index

Deep domain reference files. **Do not read by default** — consult the "Read
When" column and only read a file when your current task matches its trigger.
Code is always authoritative over these files.

## Crypto

| File | Summary | Read When |
|------|---------|-----------|
| [crypto/side-channel-patterns.md](crypto/side-channel-patterns.md) | Constant-time primitives, dangerous patterns | Touching crypto comparison/branching logic, reviewing code for timing leaks |
| [crypto/fips-integration.md](crypto/fips-integration.md) | FIPS integrity tests, CAST, algorithm restrictions | Working on FIPS builds, debugging integrity test failures |
| [crypto/tls-error-triage.md](crypto/tls-error-triage.md) | TLS/DTLS error-to-root-cause mappings | Debugging TLS handshake failures, DTLS retransmit issues |
| [crypto/openssl-compat-migration.md](crypto/openssl-compat-migration.md) | OpenSSL compat layer scope, API mapping | Implementing or debugging OPENSSL_EXTRA APIs |
| [crypto/sp-math.md](crypto/sp-math.md) | SP math variants, configure flags, naming | Working on big-number math, configure flag interactions |
| [crypto/pq-crypto.md](crypto/pq-crypto.md) | Post-quantum configure flags, hybrid TLS setup | Adding or debugging PQ/hybrid key exchange |
| [crypto/cert-chain-validation.md](crypto/cert-chain-validation.md) | Certificate error decision tree, -313/-188/-150 triage | Debugging certificate verification failures |

## Platforms

| File | Summary | Read When |
|------|---------|-----------|
| [platforms/embedded-common.md](platforms/embedded-common.md) | Stack/heap sizing, common embedded defines | Starting any embedded port or debugging memory issues |
| [platforms/esp32.md](platforms/esp32.md) | ESP32 variants, HW accel, memory constraints | Working on ESP32/ESP-IDF integration |
| [platforms/stm32.md](platforms/stm32.md) | STM32 HAL crypto by family, memory table | Working on STM32 port or HAL crypto |
| [platforms/freertos.md](platforms/freertos.md) | Task stack, heap, mutex patterns | Integrating with FreeRTOS |
| [platforms/zephyr.md](platforms/zephyr.md) | Version detection, CMake, Kconfig | Integrating with Zephyr RTOS |
| [platforms/linux-kernel-module.md](platforms/linux-kernel-module.md) | linuxkm zones, LKCAPI, no-libc constraints | Working on Linux kernel module or LKCAPI |
| [platforms/linux-tpm.md](platforms/linux-tpm.md) | /dev/tpm0 vs /dev/tpmrm0, permissions, abrmd conflicts | Integrating wolfTPM on Linux, debugging device access |
| [platforms/windows-tbs.md](platforms/windows-tbs.md) | TBS HRESULT error codes, service troubleshooting | Integrating wolfTPM on Windows, decoding 0x8028xxxx errors |

## Integrations

| File | Summary | Read When |
|------|---------|-----------|
| [integrations/configure-dependencies.md](integrations/configure-dependencies.md) | Flag dependency lookup table | Debugging configure failures, adding new --enable flags |
| [integrations/curl.md](integrations/curl.md) | vtls backend, wolfSSL+curl build flags | Integrating wolfSSL as curl's TLS backend |
| [integrations/openssh.md](integrations/openssh.md) | Crypto abstraction layers, OSP patches | Integrating wolfSSL with OpenSSH |
| [integrations/wolfprovider-openssl3.md](integrations/wolfprovider-openssl3.md) | Provider vs Engine, replace-default FIPS, opensslcoexist | Integrating wolfSSL into OpenSSL 3.x or 1.x apps |

## Products

| File | Summary | Read When |
|------|---------|-----------|
| [products/wolftpm.md](products/wolftpm.md) | TPM retry pattern, TLS device ID integration | Working on wolfTPM or TPM-backed TLS |
| [products/wolfhsm.md](products/wolfhsm.md) | HSM client-server, crypto offload via devId, RNG dispatch | Working on wolfHSM or HSM-backed crypto |
| [products/wolfjni.md](products/wolfjni.md) | Java JNI/JSSE provider, Android BKS, native dependency | Integrating wolfSSL into Java or Android |
| [products/wolfboot.md](products/wolfboot.md) | Secure boot constraints, image signing | Working on wolfBoot integration |
| [products/do178c.md](products/do178c.md) | DAL A scope, MISRA-C, safety RTOS | Working on DO-178C / aviation safety builds |

## Security

| File | Summary | Read When |
|------|---------|-----------|
| [security/cwe-patterns.md](security/cwe-patterns.md) | CWE patterns in wolfSSL context | Reviewing code for security vulnerabilities, CVE triage |
| [security/attack-principles.md](security/attack-principles.md) | Oracle attacks, trust boundaries, named TLS attacks | Reviewing protocol-level code, assessing attack surface |
| [security/embedded-threat-model.md](security/embedded-threat-model.md) | Fault injection, entropy starvation, physical attacks | Triaging embedded security reports, reviewing secure boot |

## Implementation

| File | Summary | Read When |
|------|---------|-----------|
| [implementation/embedded-transport.md](implementation/embedded-transport.md) | I/O callbacks, non-blocking retry, DTLS transport | Implementing custom I/O callbacks or transport layers |
| [implementation/hw-acceleration.md](implementation/hw-acceleration.md) | CryptoDevCb lifecycle, async crypto flow | Implementing hardware crypto backends |
| [implementation/compiler-asm-debugging.md](implementation/compiler-asm-debugging.md) | Inline asm clobber lists, NO_VAR_ASSIGN_REG, register pressure | Debugging compiler-specific assembly failures |
| [implementation/asm-optimization-matrix.md](implementation/asm-optimization-matrix.md) | Algorithm-to-platform ASM coverage, configure flags | Enabling assembly optimizations, checking platform support |

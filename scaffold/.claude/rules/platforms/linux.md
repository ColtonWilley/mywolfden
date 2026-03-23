---
paths:
  - "**/linux*"
  - "**/posix*"
---

# Linux Platform Patterns

## Build and Install
```bash
./autogen.sh  # If building from git (not release tarball)
./configure --enable-tls13 --enable-ecc ...
make
make install  # installs to /usr/local by default
ldconfig      # update shared library cache
```
- Default install: `/usr/local/lib/libwolfssl.so`, `/usr/local/include/wolfssl/`
- Custom prefix: `./configure --prefix=/opt/wolfssl`
- `pkg-config wolfssl --cflags --libs` for correct compile/link flags

## Common Linux Issues

### Shared Library Not Found
**Symptom**: "error while loading shared libraries: libwolfssl.so.XX: cannot open shared object file"
**Fix**: `ldconfig` after install, or set `LD_LIBRARY_PATH=/usr/local/lib`
- Or install to standard path: `./configure --prefix=/usr`
- For development: `export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig`

### Conflict with System OpenSSL
**Symptom**: Linking picks up system libssl instead of wolfssl.
**Fix**:
- Use explicit paths: `-I/usr/local/include -L/usr/local/lib -lwolfssl`
- Don't install wolfssl with `--prefix=/usr` if system OpenSSL is there
- OpenSSL compat headers: ensure `#include <wolfssl/openssl/ssl.h>` not `<openssl/ssl.h>`

### Static Linking
- `./configure --enable-static --disable-shared` for static-only build
- Link with: `-lwolfssl -lm -lpthread`
- Position-independent code for shared lib: `./configure --with-pic`

### Linux Kernel Module (linuxkm)
### Linux Kernel Module (linuxkm)
- wolfSSL can run as a Linux kernel module
- Built from `linuxkm/` directory
- Used for kernel-space TLS (KTLS), WireGuard crypto, LKCAPI integration
- Different build process: `make -C linuxkm`
- No user-space dependencies (no libc, no malloc — uses kernel kmalloc)

#### linuxkm_wc_port.h Zone Architecture

`linuxkm/linuxkm_wc_port.h` has distinct macro visibility zones separated
by `#ifdef BUILDING_WOLFSSL`. The zone a macro is defined in determines
which compilation units can see it:

- **Pre-guard zone** (before `#ifdef BUILDING_WOLFSSL`): Visible to ALL
  consumers — both wolfSSL internal files and external callers. Public
  API declarations, entropy framework setup, and extern function decls
  go here.
- **BUILDING_WOLFSSL zone**: Only visible when compiling wolfSSL itself.
  Kernel header includes, LKCAPI registration macros, internal function
  pointers, and implementation details go here.
- **`!BUILDING_WOLFSSL` zone**: Only visible to external callers. Minimal
  API surface (e.g., vector register save/restore).
- **Post-guard zone** (after both guards close): Visible to everyone.
  Mutex/spinlock selection, FIPS name mappings.

Moving a `#define` between zones changes who can see it. Example:
`LINUXKM_LKCAPI_REGISTER_HASH_DRBG_DEFAULT` is defined inside the
BUILDING_WOLFSSL zone so that `random.c` (compiled as part of wolfSSL)
can gate out `get_random_bytes()` calls that would recurse when
wolfCrypt IS the kernel's default RNG. If this define were in the
pre-guard zone, it would leak to external consumers that don't need it.

#### LKCAPI Handle-Based API Convention

#### LKCAPI Macro Gate Chain

LKCAPI registration uses a cascading macro chain where umbrella macros
auto-enable specific registrations unless explicitly suppressed:

`LINUXKM_LKCAPI_REGISTER_ALL` → enables individual algorithm registrations
→ each suppressible via `LINUXKM_LKCAPI_DONT_REGISTER_<algo>`

When tracing why a particular LKCAPI algorithm is or isn't registered,
follow the chain in `linuxkm_wc_port.h`'s BUILDING_WOLFSSL zone. The
auto-enable `#define` is conditional on the absence of multiple
suppression macros.

Kernel-facing LKCAPI functions receive explicit kernel crypto handles
(`struct crypto_rng *`, `struct crypto_shash *`, etc.) rather than
accessing wolfCrypt globals. The handle carries the algorithm context
via the kernel's `crypto_tfm` mechanism:

- Extract wolfCrypt state: `crypto_rng_ctx(tfm)` → private context
- Validate ownership: compare `tfm->base.__crt_alg->cra_init` against
  wolfCrypt's init function pointer to confirm the handle belongs to
  wolfCrypt's registered algorithm
- Never access global wolfCrypt RNG state directly from LKCAPI callbacks

This pattern is consistent across all LKCAPI glue files (`lkcapi_glue.c`,
`lkcapi_sha_glue.c`). New kernel-facing functions must follow it.
### Cross-Compilation
```bash
./configure --host=arm-linux-gnueabihf \
  CC=arm-linux-gnueabihf-gcc \
  --enable-ecc --enable-tls13
```
- Set `CC`, `AR`, `RANLIB` for cross toolchain
- `--host` specifies target platform
- May need `--build` if autoconf can't detect build system

## Performance on Linux
- Assembly optimizations: `--enable-aesni` (x86 AES-NI), `--enable-intelasm` (x86 general)
- ARM: `--enable-armasm` for NEON/crypto extensions
- Multi-threaded: wolfSSL is thread-safe by default on Linux
- epoll integration: use non-blocking wolfSSL with `wolfSSL_set_using_nonblock()`

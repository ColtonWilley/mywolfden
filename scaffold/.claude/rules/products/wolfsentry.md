---
paths:
  - "repos/wolfsentry/**"
  - "**/wolfsentry/**"
---

# wolfSentry Patterns

## Overview
wolfSentry is wolfSSL's embedded IDPS (Intrusion Detection and Prevention System) -- an embedded firewall engine with both static and fully dynamic rules. It provides prefix-based and wildcard-capable lookup of hosts/netblocks qualified by interface, address family, protocol, port, and other traffic parameters. Beyond firewall rules, wolfSentry acts as a dynamically configurable logic hub, associating user-defined events with user-defined actions contextualized by connection attributes.

wolfSentry is designed for resource-constrained environments: dynamic firewalling can add as little as 64KB code and 32KB volatile state. It runs on FreeRTOS, Zephyr, NuttX, VxWorks, Nucleus, Green Hills Integrity, and bare-metal targets on ARM Cortex-M and other embedded CPUs.

## JSON Configuration
wolfSentry is configured via JSON documents conforming to RFC 8259. The three essential API calls for initialization are:
1. `wolfsentry_init()` -- create the engine context
2. `wolfsentry_config_json_oneshot()` -- load a full JSON config
3. `wolfsentry_install_lwip_filter_callbacks()` -- activate lwIP integration

Minimal JSON config structure:
```json
{
    "wolfsentry-config-version": 1,
    "config-update": {
        "max-connection-count": 10,
        "penalty-box-duration": "5m",
        "derog-thresh-for-penalty-boxing": 4
    },
    "default-policies": {
        "default-policy": "reject"
    },
    "routes": [
        {
            "family": "inet",
            "protocol": "tcp",
            "direction-in": true,
            "green-listed": true,
            "remote": {
                "address": "192.168.1.0",
                "prefix-bits": 24
            },
            "local": { "port": 443 }
        }
    ]
}
```

Key JSON ordering rule: `"wolfsentry-config-version"` must appear first, and event definitions must precede any routes or policies that reference them. This enables efficient SAX-style streaming parse.

Duration values accept unit suffixes: `"300"` (seconds), `"5m"` (minutes), `"1h"` (hours), `"1d"` (days).

### Transactional Config Reload
Use `WOLFSENTRY_CONFIG_LOAD_FLAG_LOAD_THEN_COMMIT` to atomically swap configurations -- the old config remains active until the new one loads successfully. On error, the running config is unchanged. This is the recommended flag for production config reloads.

## lwIP Integration
wolfSentry integrates with lwIP via a patchset in the `lwip/` subdirectory. The patch adds a `LWIP_PACKET_FILTER_API` to lwIP without adding new `.c` files.

Setup steps:
1. Apply the lwIP patch: `patch -p1 < wolfsentry/lwip/LWIP_PACKET_FILTER_API.patch`
2. Add `#define LWIP_PACKET_FILTER_API 1` to `lwipopts.h`
3. Call `wolfsentry_install_lwip_filter_callbacks()` with event masks for each protocol layer (ethernet, IP, ICMP, TCP, UDP)

The patch supports lwIP v2.1.3 and newer. Two patch variants are provided: `.patch` for LF line endings (Linux/git sources) and `.CRLF.patch` for Windows/zip sources.

Filter callbacks cover events: binding, connecting, accepting, receiving, sending, closed, remote-reset, address/port unreachable, and errors. Pass `0` for any protocol layer gated out of the lwIP build.

## wolfSSL Integration
wolfSSL has built-in wolfSentry hooks for application-level TLS connection filtering:
- Configure wolfSSL with `--enable-wolfsentry` (and `--with-wolfsentry=/install/path` if non-standard)
- Key functions in wolfSSL: `wolfsentry_store_endpoints()`, `wolfSentry_NetworkFilterCallback()`, `wolfsentry_setup()`
- Test client/server accept `--wolfsentry-config <file>` for JSON policy loading
- Code is gated on `WOLFSSL_WOLFSENTRY_HOOKS` in wolfSSL headers

## FreeRTOS Integration
Build for FreeRTOS on ARM32:
```bash
make HOST=arm-none-eabi RUNTIME=FreeRTOS-lwIP \
    FREERTOS_TOP=../FreeRTOS LWIP_TOP=../lwip \
    EXTRA_CFLAGS="-mcpu=cortex-m7"
```

`FREERTOS_TOP` must contain `FreeRTOS/Source` directly beneath it. `LWIP_TOP` must contain `src` directly beneath it.

For STM32 projects using STM32CubeIDE, create `wolfsentry/wolfsentry/wolfsentry_options.h`:
```c
#define FREERTOS
#define WOLFSENTRY_SINGLETHREADED
#define WOLFSENTRY_LWIP
#define WOLFSENTRY_NO_PROTOCOL_NAMES
#define WOLFSENTRY_NO_POSIX_MEMALIGN
```

Omit `WOLFSENTRY_SINGLETHREADED` if using multithreaded lwIP, but this requires semaphore support in the runtime.

## Build Options
Smallest possible build (no POSIX dependencies):
```bash
make STATIC=1 SINGLETHREADED=1 NO_STDIO=1 \
    EXTRA_CFLAGS="-DWOLFSENTRY_NO_CLOCK_BUILTIN -DWOLFSENTRY_NO_MALLOC_BUILTIN"
```
This requires the application to provide allocator and time callbacks via `struct wolfsentry_host_platform_interface` passed to `wolfsentry_init()`.

Key build flags:
- `SINGLETHREADED` -- omit thread safety logic (no semaphores needed)
- `NO_JSON` -- omit JSON configuration support
- `NO_STDIO` -- omit stdio stream I/O dependencies
- `WOLFSENTRY_NO_CLOCK_BUILTIN` -- app must provide time callbacks
- `WOLFSENTRY_NO_MALLOC_BUILTIN` -- app must provide allocator callbacks
- `WOLFSENTRY_NO_IPV6` -- omit IPv6 address family support
- `LWIP=1` -- activate lwIP-appropriate build settings
- `RUNTIME=FreeRTOS-lwIP` -- set FreeRTOS+lwIP runtime target

Build and run tests: `make -j test`
Build in alternate directory: `make BUILD_TOP=./build -j test`

## Events and Actions
Events associate labels with action lists. Actions fire at specific lifecycle points:
- `insert-actions` -- when a route is created
- `match-actions` -- when traffic matches a route
- `delete-actions` -- when a route is removed
- `decision-actions` -- when final accept/reject decision is made

The built-in `%track-peer-v1` action automatically creates dynamic routes for new peers, using the event's `aux-parent-event` as the new route's parent. This enables automatic penalty-boxing: after `derog-thresh-for-penalty-boxing` derogatory events, the peer is blocked for `penalty-box-duration`.

## Common Issues

### Routes Not Matching
- Wildcard flags are set implicitly -- if a field is omitted from JSON, its wildcard flag is set automatically. If you specify `"family": "inet"`, only IPv4 traffic matches.
- Check `direction-in`/`direction-out` -- a route with neither set matches no traffic by direction.
- Verify address family: `"inet"` for IPv4, `"inet6"` for IPv6, `"link"` for MAC/Ethernet.

### Penalty Box Not Working
- `derog-thresh-for-penalty-boxing` must be nonzero in the event's config (or global `config-update`)
- Dynamic routes require an event with `%track-peer-v1` in its `post-actions` and an `aux-parent-event` defining the tracked route's behavior
- `penalty-box-duration` of `0` means routes stay penalty-boxed indefinitely (no auto-release)

### Build Failures on Embedded
- Missing `inet_ntop()`: lwIP provides this -- ensure lwIP headers are on the include path
- 32-bit atomic issues: on 32-bit targets, avoid atomic operations on 64-bit values. Build with `SINGLETHREADED=1` or provide custom atomics via `WOLFSENTRY_HAVE_NONGNU_ATOMICS`
- Linker errors for `pthread_*` or `sem_*`: add `SINGLETHREADED=1` to eliminate POSIX threading dependency
- `clock_gettime` missing: add `-DWOLFSENTRY_NO_CLOCK_BUILTIN` and provide time callbacks

### STM32CubeIDE Integration
- Add wolfsentry source directory to project via Project > Properties > C/C++ General > Paths and Symbols > Source Location
- Filter out `**/unittests.c` and `**/examples` to avoid `main()` conflicts
- STM32CubeMX code regeneration overwrites `ethernetif.c` changes -- re-apply MAC filter hooks after regeneration

### Config Load Errors
- JSON parse errors return detailed messages in the error buffer passed to `wolfsentry_config_json_oneshot()`
- Element ordering violations (e.g., route referencing an undefined event) cause load failure
- Use `WOLFSENTRY_CONFIG_LOAD_FLAG_DRY_RUN` to validate config without affecting the running policy

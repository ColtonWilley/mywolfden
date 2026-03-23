---
paths:
  - "**/embos*/**"
---

# SEGGER embOS Ultra — External Platform Summary

## Current State

- **Latest version:** embOS Ultra v5.20.0 (March 2025)
- **Vendor:** SEGGER Microcontroller GmbH (Monheim am Rhein, Germany)
- **Documentation:** UM01076 — User Guide & Reference Manual for embOS-Ultra and embOS-Ultra-MPU
- **License:** Commercial license; object code package also available under SEGGER Friendly License (SFL) for evaluation and non-commercial use
- **Editions:**
  - **embOS-Classic** — Traditional periodic-tick RTOS (used in every J-Link and J-Trace)
  - **embOS-Ultra** — Cycle-based scheduling with flexible tick (no periodic tick interrupt)
  - **embOS-MPU** — Adds hardware memory protection / task sandboxing
  - **embOS-Safe** — Pre-certified (IEC 61508 SIL 3, IEC 62304 Class C, ISO 26262 ASIL D)

---

## Architecture

### Kernel Lifecycle

```c
int main(void) {
    OS_Init();       // Initialize embOS kernel
    OS_InitHW();     // Initialize hardware (BSP)
    OS_TASK_CREATE(&TCB, "Task", priority, TaskFunc, Stack);
    OS_Start();      // Start scheduler (does not return)
    return 0;
}
```

- `OS_Init()` must be the first embOS call
- `OS_Start()` enables interrupts and begins scheduling
- After `OS_Start()`, the main stack is reused by the kernel — local variables from `main()` are no longer valid unless `OS_ConfigStop()` is used

### Scheduling

- **Priority-controlled preemptive scheduling** — highest-priority ready task always runs
- **Round-robin** for tasks at the same priority (configurable time slice per task)
- Up to **4,294,967,296 priority levels** (32-bit priority value)
- Higher numeric value = higher priority
- Preemption can be disabled in critical regions

### embOS-Ultra vs embOS-Classic

| Feature | embOS-Classic | embOS-Ultra |
|---------|---------------|-------------|
| Tick model | Periodic (typically 1ms) | Flexible / on-demand |
| Time units in API | System ticks | Milliseconds |
| Timer interrupt | Every tick (even when idle) | Only when scheduler needs action |
| Time resolution | Limited to tick period | CPU cycle resolution |
| Power efficiency | Tick interrupts waste power when idle | No unnecessary interrupts |
| Hardware requirement | Timer for periodic interrupt | Timer + continuously running counter |

embOS-Ultra's cycle-based scheduling eliminates periodic tick interrupts entirely. The hardware timer fires only when a time-based action (delay expiry, timeout, round-robin slice) is needed. This significantly reduces power consumption in idle periods.

### Task Model

- All tasks are **threads** (shared memory layout, same access rights)
- No process isolation in base embOS (embOS-MPU adds per-task sandboxing)
- Each task has: program code (ROM), dedicated stack (RAM), task control block / TCB (RAM)
- Task states: **Ready**, **Running**, **Waiting** (delay, semaphore, mutex, event, mailbox, queue), **Non-existent**
- Unlimited number of tasks (limited only by available memory)

### Task Context and Stacks

- **Task stack**: per-task, stores registers, return addresses, local variables
- **System stack**: used by `main()`, scheduler, software timers; reused after `OS_Start()`
- **Interrupt stack**: optional separate stack for ISRs (reduces per-task stack requirements)
- Stack overflow detection available in debug/stack-check library modes
- Task context extension supported via save/restore hooks (`OS_SUPPORT_SAVE_RESTORE_HOOK`)

---

## Synchronization Primitives

### Mutexes (relevant to wolfSSL threading layer)

Mutexes manage exclusive access to resources with **recursive locking** (counter-based) and **priority inheritance**.

| API | Description |
|-----|-------------|
| `OS_MUTEX_Create(&mutex)` | Create mutex (counter=0, unlocked) |
| `OS_MUTEX_LockBlocked(&mutex)` | Acquire, blocking if held by another task; supports priority inheritance |
| `OS_MUTEX_Lock(&mutex)` | Try-acquire; returns 0 if unavailable, non-zero if acquired |
| `OS_MUTEX_LockTimed(&mutex, ms)` | Acquire with millisecond timeout (embOS-Ultra) |
| `OS_MUTEX_Unlock(&mutex)` | Release; must be called same number of times as Lock |
| `OS_MUTEX_Delete(&mutex)` | Destroy mutex |
| `OS_MUTEX_GetOwner(&mutex)` | Returns owning task's TCB pointer (NULL if free) |
| `OS_MUTEX_GetValue(&mutex)` | Returns usage counter (0 = available) |
| `OS_MUTEX_IsMutex(&mutex)` | Check if mutex has been created |

- A task cannot release a mutex it does not own (enforced in debug builds)
- Recursive: same task can lock multiple times; counter tracks depth
- Priority inheritance: if high-priority task blocks on mutex held by low-priority task, the low-priority task temporarily inherits the higher priority

### Semaphores

| API | Description |
|-----|-------------|
| `OS_SEMAPHORE_Create(&sema, initial_count)` | Create counting or binary semaphore |
| `OS_SEMAPHORE_TakeBlocked(&sema)` | Wait for token (decrements counter) |
| `OS_SEMAPHORE_Take(&sema)` | Try-take (non-blocking) |
| `OS_SEMAPHORE_TakeTimed(&sema, ms)` | Take with timeout |
| `OS_SEMAPHORE_Give(&sema)` | Release token (increments counter); callable from ISR |
| `OS_SEMAPHORE_GetValue(&sema)` | Returns current count |
| `OS_SEMAPHORE_Delete(&sema)` | Destroy semaphore |

### Other Primitives

- **Task Events**: per-task 32-bit event flags (`OS_TASKEVENT_Set()`, `OS_TASKEVENT_GetBlocked()`)
- **Event Objects**: standalone event objects with mask-based wait (`OS_EVENT_Set()`, `OS_EVENT_GetMaskBlocked()`)
- **Mailboxes**: fixed-size message buffers (`OS_MAILBOX_Create()`, `OS_MAILBOX_Put()`, `OS_MAILBOX_GetBlocked()`)
- **Queues**: variable-size message queues (`OS_QUEUE_Create()`, `OS_QUEUE_Put()`, `OS_QUEUE_GetPtrBlocked()`)
- **Readers-Writer Locks**: `OS_RWLOCK` for concurrent read / exclusive write access
- **Multi Object Wait**: wait on multiple objects simultaneously with condition routines
- **Software Timers**: one-shot or periodic callbacks (`OS_TIMER_Create()`, `OS_TIMER_Start()`)
- **Watchdog**: software watchdog with per-task monitoring

---

## Memory Management

### Heap (Thread-Safe)

```c
void* OS_HEAP_malloc(unsigned int size);
void  OS_HEAP_free(void* ptr);
void* OS_HEAP_realloc(void* ptr, unsigned int size);
```

These are thread-safe wrappers around standard C `malloc`/`free`/`realloc`, serialized using an internal mutex. Not available in `OS_LIBMODE_SAFE`.

Many modern toolchains provide hook functions (implemented by embOS) that make the standard `malloc`/`free` thread-safe directly — check the CPU/compiler-specific embOS manual.

### Fixed Block Memory Pools

```c
OS_MEMPOOL_Create(&pool, buffer, num_blocks, block_size);
void* OS_MEMPOOL_Alloc(&pool);
void* OS_MEMPOOL_AllocBlocked(&pool);       // blocks if empty
void* OS_MEMPOOL_AllocTimed(&pool, ms);     // timeout variant
void  OS_MEMPOOL_Free(&pool, ptr);
```

Fixed block pools eliminate fragmentation — useful for deterministic embedded allocations.

---

## Interrupts

### ISR Pattern

```c
void MyISR(void) {
    OS_INT_Enter();        // Notify embOS of ISR entry
    // ... handle interrupt ...
    OS_INT_Leave();        // Notify embOS of ISR exit; may trigger task switch
}
```

- `OS_INT_Enter()` / `OS_INT_Leave()` bracket embOS-aware interrupts
- ISRs may call non-blocking embOS APIs: `OS_SEMAPHORE_Give()`, `OS_MAILBOX_Put()`, `OS_TASKEVENT_Set()`, etc.
- ISRs must NOT call blocking APIs (`*Blocked`, `*Timed`)
- Nested interrupts are supported
- **Zero-latency interrupts**: interrupts above the embOS-managed priority threshold run without any embOS latency (cannot call embOS APIs)

### Interrupt Latency

- embOS disables interrupts for very short periods during critical kernel operations
- Zero-latency interrupts bypass this entirely for time-critical ISRs
- Exact latency depends on CPU, clock speed, and library mode

---

## MPU — Memory Protection (embOS-Ultra-MPU)

- Adds **task sandboxing** using hardware MPU/MMU
- Unprivileged tasks have restricted memory access and limited embOS API
- Even if an unprivileged task crashes, other tasks and the RTOS continue unaffected
- Privileged tasks and the kernel run without MPU restrictions
- Available only for CPUs with hardware MPU/MMU (e.g., Cortex-M with MPU)
- Per-task memory regions configured via `OS_MPU_SetAllowedRegion()`

---

## Library Modes

| Mode | Debug | Stack Check | Profiling | API Trace | Round-Robin | Names | Context Ext |
|------|-------|-------------|-----------|-----------|-------------|-------|-------------|
| `OS_LIBMODE_XR` | | | | | | | |
| `OS_LIBMODE_R` | | | | | yes | yes | yes |
| `OS_LIBMODE_S` | | yes | | | yes | yes | yes |
| `OS_LIBMODE_SP` | | yes | yes | | yes | yes | yes |
| `OS_LIBMODE_D` | yes | yes | | | yes | yes | yes |
| `OS_LIBMODE_DP` | yes | yes | yes | | yes | yes | yes |
| `OS_LIBMODE_DT` | yes | yes | yes | yes | yes | yes | yes |
| `OS_LIBMODE_SAFE` | yes | yes | | yes | yes | yes | yes |

- Use `OS_LIBMODE_DP` during development (debug + profiling)
- Use `OS_LIBMODE_R` or `OS_LIBMODE_XR` for production (minimal overhead)
- `OS_Config.h` auto-selects `OS_LIBMODE_DP` when `DEBUG=1`, `OS_LIBMODE_R` otherwise

### Key Compile-Time Switches

| Switch | Description | Default (DP) |
|--------|-------------|--------------|
| `OS_DEBUG` | Runtime debug checks | 1 |
| `OS_SUPPORT_STACKCHECK` | Stack overflow detection | 1 |
| `OS_SUPPORT_PROFILE` | Profiling / SystemView | 1 |
| `OS_SUPPORT_RR` | Round-robin scheduling | 1 |
| `OS_SUPPORT_TIMER` | Software timers | 1 |
| `OS_SUPPORT_TRACKNAME` | Task/object names | 1 |
| `OS_SUPPORT_SAVE_RESTORE_HOOK` | Task context extensions | 1 |
| `OS_SUPPORT_PERIPHERAL_POWER_CTRL` | Peripheral power management | 1 |
| `OS_INIT_EXPLICITLY` | Explicit variable initialization | 0 |

---

## Resource Usage (Cortex-M, OS_LIBMODE_XR)

Values from embOS-Ultra Cortex-M ES V5.18.1.0:

| Component | Memory Type | Size |
|-----------|-------------|------|
| Kernel | ROM | ~2100 bytes |
| Kernel | RAM | ~128 bytes |
| Task control block (TCB) | RAM | 48 bytes |
| Software timer | RAM | 32 bytes |
| Event object | RAM | 12 bytes |
| Mutex | RAM | 16 bytes |
| Semaphore | RAM | 8 bytes |
| Readers-Writer Lock | RAM | 28 bytes |
| Mailbox | RAM | 24 bytes |
| Queue | RAM | 32 bytes |
| Watchdog | RAM | 24 bytes |
| Fixed block memory pool | RAM | 32 bytes |

### Context Switch Performance

| Target | embOS Version | CPU Freq | Time | Cycles |
|--------|---------------|----------|------|--------|
| Renesas RZ | V5.14.0.0 | 400 MHz | 0.48 us | 192 |
| Xilinx XZ7Z007S | V5.14.0.0 | 600 MHz | 0.43 us | 258 |
| ST STM32H743 | V5.14.0.0 | 200 MHz | 1.41 us | 282 |

---

## wolfSSL Integration Notes

### Threading Layer Mapping

wolfSSL's mutex abstraction (`wolfssl/wolfcrypt/wc_port.h`) maps to embOS as follows:

| wolfSSL abstraction | embOS API |
|---------------------|-----------|
| `wolfSSL_Mutex` type | `OS_MUTEX` |
| `wc_InitMutex()` | `OS_MUTEX_Create()` |
| `wc_LockMutex()` | `OS_MUTEX_LockBlocked()` |
| `wc_UnLockMutex()` | `OS_MUTEX_Unlock()` |
| `wc_FreeMutex()` | `OS_MUTEX_Delete()` |

embOS mutexes natively support recursive locking and priority inheritance — both are beneficial for wolfSSL's threading model.

### Memory Allocation

wolfSSL's `XMALLOC`/`XFREE`/`XREALLOC` can be mapped to:

**Option A — embOS thread-safe heap (recommended if libc malloc available):**
```c
#define XMALLOC(s, h, t)     OS_HEAP_malloc((s))
#define XFREE(p, h, t)       { if ((p)) OS_HEAP_free((p)); }
#define XREALLOC(p, n, h, t) OS_HEAP_realloc((p), (n))
```

**Option B — Standard malloc (if toolchain hooks make it thread-safe via embOS):**
No override needed; the toolchain's `malloc`/`free` are already thread-safe.

**Option C — Static memory (no dynamic allocation):**
```c
#define WOLFSSL_STATIC_MEMORY
```

### Networking / I/O Callbacks

embOS does not include a TCP/IP stack. It is typically paired with:
- **SEGGER emNet** (formerly embOS/IP) — SEGGER's TCP/IP stack
- **lwIP** — lightweight IP stack
- Custom socket layers

Implement custom I/O callbacks for wolfSSL:
```c
#define WOLFSSL_USER_IO
/* Then register via wolfSSL_SetIOSend() / wolfSSL_SetIORecv() */
```

### Stack Sizing

wolfSSL TLS operations require substantial stack depth. For embOS tasks performing TLS:
- **Minimum 8 KB** for RSA-2048 / ECC-256
- **12-20 KB** for larger keys or certificate chains
- Use `WOLFSSL_SMALL_STACK` to reduce stack pressure
- Enable stack checking (`OS_LIBMODE_S` or higher) during development to detect overflows

### Time Source

wolfSSL needs a time source for certificate validation. Implement `XTIME()` using:
- embOS time API: `OS_TIME_GetTime_ms()` returns system time in milliseconds
- Hardware RTC if available
- NTP client if networking is present

### Entropy / RNG

Provide hardware RNG or custom seed:
```c
#define CUSTOM_RAND_GENERATE_BLOCK  my_rng_function
```

### Certificate Loading

Most embOS targets lack a filesystem. Use buffer-based loading:
```c
wolfSSL_CTX_load_verify_buffer(ctx, ca_cert, ca_cert_len, SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_certificate_buffer(ctx, dev_cert, dev_cert_len, SSL_FILETYPE_ASN1);
wolfSSL_CTX_use_PrivateKey_buffer(ctx, dev_key, dev_key_len, SSL_FILETYPE_ASN1);
```

Or use the `NO_FILESYSTEM` define:
```c
#define NO_FILESYSTEM
```

---

## Board Support Packages

embOS BSPs are provided as source code and implement hardware-specific initialization:

| Routine | Purpose |
|---------|---------|
| `OS_InitHW()` | Initialize clocks, timer, interrupt controller |
| `OS_Idle()` | Called when no task is ready; implement power-save modes here |
| `OS_COM_Init()` | Initialize UART for embOSView communication |
| `OS_INT_HANDLER_*` | Interrupt service routines for embOS timer |

BSP routines are in `Start/BoardSupport/<Vendor>/<Device>/` directories.

---

## Supported Development Tools

- **SEGGER Embedded Studio** — primary IDE
- **IAR Embedded Workbench** (EWARM)
- **Keil MDK / RVDS**
- **GCC / ARM GCC**
- **Rowley CrossWorks**
- **CodeWarrior**

embOS supports C90 through C17 and C++98 through C++20. Sources are compiled with a C compiler; C++ applications link against embOS C libraries.

---

## Key Files

| File | Purpose |
|------|---------|
| `RTOS.h` | Master include file for embOS API (composed from CPU-specific and generic parts) |
| `OS_Config.h` | Library mode auto-selection; customizable per-project |
| `BSP.h` | Board support package header |
| `Start/BoardSupport/` | BSP source code per vendor/device |
| `Start/Inc/` | embOS headers |
| `Start/Lib/` | Pre-built embOS libraries (one per library mode) |
| `CPU/` | Architecture-specific assembler and C files (context switch) |
| `GenOSSrc/` | Generic embOS kernel sources (source code package only) |

---

## Common Integration Issues

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Stack overflow / hard fault in TLS task | Task stack too small for wolfSSL operations | Increase task stack; minimum 8 KB for RSA-2048; use `WOLFSSL_SMALL_STACK` |
| `OS_Error()` called with OS_ERR_ILLEGAL_IN_ISR | Blocking wolfSSL call made from ISR context | Ensure all TLS operations run in a proper task context, not ISR or timer callback |
| `OS_Error()` with OS_ERR_MUTEX_OWNER | `OS_MUTEX_Unlock()` called by wrong task | Verify wolfSSL mutex lock/unlock pairs are in same task context |
| Deadlock during TLS handshake | Two tasks locking mutexes in different order | Ensure consistent lock ordering; use `OS_MUTEX_LockTimed()` for deadlock detection |
| `OS_HEAP_malloc()` returns NULL | Insufficient heap memory | Increase heap size or use `WOLFSSL_STATIC_MEMORY` to avoid dynamic allocation |
| Timeout behavior differs from expected | embOS-Ultra uses milliseconds, not ticks | Verify timeout values are in ms; `OS_TIME_ConfigSysTimer()` must be called before timed APIs |
| Power consumption higher than expected | wolfSSL polling or busy-waiting in I/O callback | Use blocking socket calls or `OS_TASK_Delay_ms()` to yield in I/O wait loops |
| Certificate validation fails | No time source configured | Implement `XTIME()` using RTC or `OS_TIME_GetTime_ms()` with epoch offset |

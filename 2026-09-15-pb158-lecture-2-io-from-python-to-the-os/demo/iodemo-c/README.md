---
created: 2026-09-15
tags:
  - talk
  - demo
  - operating-systems
  - tracing
---

# `iodemo.c` — the program both traces watch

Nine lines of C. It is introduced in section 4 (source, compile, run) and
traced on both platforms in section 5. It prints nothing on purpose; the trace
does the talking. See [`../README.md`](../README.md) for why one program, and
why it is silent.

## What it does, and what to look for

| step | source | what the trace should show |
|---|---|---|
| 1 | `fopen("no-such-file.txt", "rb")` | the failure, and **how each platform reports it** |
| 2 | `fopen(path, "wb")` | the open, and **how each platform names the file** |
| 3 | three `fwrite` calls, 14 bytes | **how many** write calls arrive |
| 4 | `fclose`, **return value checked** | the flush, then the close |

**Step 3 is the one to dwell on.** Three writes in the source, fourteen bytes,
and the buffer hands them down together. Three source lines, one trace line —
which is takeaway 2 and objective 4 in a single artefact you can point at.

**Step 1 exists only to make the error path visible.** A clean run returns
success all the way down, and the most interesting Windows-versus-Linux
difference in the whole trace never appears. Linux reports a single `errno`.
Windows reports an `NTSTATUS` together with the Win32 error it translates into
— two error namespaces in one return value.

**Step 4 checks the return value of `fclose`, deliberately.** A failure from
any of the three `fwrite` calls cannot surface at the call that caused it — the
bytes only reached a buffer. It surfaces at the flush, which means it arrives
at `fclose` attached to no particular write. That is section 6's material, and
almost no real code checks it.

Also watch for a **handle** on one side and a **file descriptor** on the other,
and for the `\??\` object-manager path prefix on the Windows side — a string a
Win32 program never types.

## Build and trace

### Linux, natively

```sh
make            # builds ./iodemo
make trace      # strace -e trace=openat,write,close ./iodemo iodemo.out
make count      # ./iodemo iodemo.out --count  — the kernel's own write count
```

### Linux, in a container

The `Dockerfile` is a Debian box with `gcc`, `make`, `strace` and `ltrace` —
what a lab machine has after `apt install`. It builds the program at image
build time.

```sh
make image              # docker build -t pb158-iodemo-c .
make container-trace    # docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c
make container-count    # docker run --rm pb158-iodemo-c ./iodemo iodemo.out --count
```

`--cap-add SYS_PTRACE` is belt and braces. Docker drops `CAP_SYS_PTRACE` by
default and, on kernels before 4.8, its default seccomp profile blocks the
`ptrace` call outright
([Docker: seccomp security profiles](https://docs.docker.com/engine/security/seccomp/)).
On a current Docker and kernel a tracer may trace the container's *own child*
without the capability — verified 2026-09-15 on Docker 29.7 — but the flag
costs nothing, and without it the failure mode is a silent `PTRACE_TRACEME`
error on an older host. The `--count` run needs no capability: `/proc/self/io`
is the kernel's own accounting and is readable without a tracer. Anything else the lecture
mentions runs the same way, for example
`docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c ltrace ./iodemo iodemo.out`
to see the three `fwrite` calls that `strace` collapses into one `write`.

### Windows

```bat
nmake /f Makefile.msvc          REM from a Developer Command Prompt
nmake /f Makefile.msvc trace    REM NtTrace -filter NtCreateFile,NtWriteFile,NtClose iodemo.exe iodemo.out
```

`cl.exe` is not on `PATH` in an ordinary terminal — it needs the Developer
Command Prompt — and MSVC ships `nmake`, not GNU make. Hence two makefiles.
NtTrace needs **no administrator rights**: it is a debugger, not a driver.

## Captured in the container, 2026-09-15

Docker 29.7, `debian:trixie-slim`, arm64. Verbatim; the tail of each run.

`make container-trace`:

```text
openat(AT_FDCWD, "no-such-file.txt", O_RDONLY) = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "iodemo.out", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 3
write(3, "one\ntwo\nthree\n", 14)       = 14
close(3)                                = 0
+++ exited with 0 +++
```

`docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c ltrace ./iodemo iodemo.out`:

```text
fopen("no-such-file.txt", "rb")                  = nil
fopen("iodemo.out", "wb")                        = 0xc93b292312a0
fwrite("one\n", 1, 4, 0xc93b292312a0)            = 4
fwrite("two\n", 1, 4, 0xc93b292312a0)            = 4
fwrite("three\n", 1, 6, 0xc93b292312a0)          = 6
fclose(0xc93b292312a0)                           = 0
+++ exited (status 0) +++
```

Three `fwrite` calls under `ltrace`, one `write` under `strace`: the C library
buffer doing its job, on one screen. `make container-count` printed
`write operations counted by the kernel: 7` — the program's one write plus
the loader's; compare two runs, never read one.

## `--count`

With `--count` the program prints, at the end, how many **write operations the
kernel has counted for this process** — from the operating system's own
per-process accounting, not from any tracer:

| platform | where the kernel keeps it | what it counts |
|---|---|---|
| Linux | `/proc/self/io`, field `syscw` | "number of write syscalls" — proc_pid_io(5) |
| Windows | `GetProcessIoCounters` → `IO_COUNTERS.WriteOperationCount` | "the number of write operations performed" — winnt.h |

Off by default: the report is itself a write to the console, and a traced run
should stay exactly four steps. Two limits: the counters record I/O
*operations*, not every crossing (a seek is not in `syscw`), and the count
includes the runtime's own start-up writes — compare two runs, never trust one.

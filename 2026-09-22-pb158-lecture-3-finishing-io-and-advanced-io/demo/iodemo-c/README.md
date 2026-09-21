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

**NtTrace needs its `NtTrace.cfg` beside the executable** — the table of
native entry points for the running Windows version; without it the tracer
has nothing to break on. Download it from the same release as
`NtTrace64.exe`. NtTrace ships for x86 and x64 only, no ARM64 build; on an
ARM64 Windows machine, `NtTrace64.exe` traced an x64-built `iodemo.exe` under
the x64 emulation layer (Ondra, 2026-09-15). Build the program for x64 there,
not for ARM64.

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

## Captured on Windows, 2026-09-15

Built with `nmake /f Makefile.msvc` (x64) and run by Ondra on an ARM64 Windows
machine under the x64 emulation layer; Windows version not recorded. Verbatim:

```text
> iodemo.exe --count
write operations counted by the kernel: 1
```

One write operation for the whole process: the three `fwrite` calls left the
buffer as one `WriteFile`, `fclose` added nothing, and — unlike the Linux run,
where the loader had already made six of the seven — nothing before `main`
counted as a write operation at all. Same fourteen bytes, same one write,
two kernels agreeing on the number that matters and disagreeing on what
surrounds it.

**The Windows half of the matched pair** — `NtTrace64-IODEMO-Output.txt` in
this folder, 45 lines, run by Ondra the same day with the makefile's `trace`
target (the three-name filter, `iodemo.exe iodemo.out`). After the loader's
own `NtCreateFile`/`NtClose` traffic and the `Initial breakpoint`, the
program's four steps, verbatim:

```text
NtCreateFile(FileHandle=0xe14f7f958, DesiredAccess=SYNCHRONIZE|GENERIC_READ|0x80, ObjectAttributes=0x58:"no-such-file.txt", IoStatusBlock=0xe14f7f990, AllocationSize=null, FileAttributes=0x80, ShareAccess=3, CreateDisposition=1, CreateOptions=0x60, EaBuffer=null, EaLength=0) => 0xc0000034 [2 'The system cannot find the file specified.']
NtCreateFile(FileHandle=0xe14f7f958 [0x124], DesiredAccess=SYNCHRONIZE|GENERIC_WRITE|0x80, ObjectAttributes=0x58:"iodemo.out", IoStatusBlock=0xe14f7f990 [0/3], AllocationSize=null, FileAttributes=0x80, ShareAccess=3, CreateDisposition=5, CreateOptions=0x60, EaBuffer=null, EaLength=0) => 0
NtWriteFile(FileHandle=0x124, Event=0, ApcRoutine=null, ApcContext=null, IoStatusBlock=0xe14f7fb90 [0/0xe], Buffer=0x12b65d78050, Length=0xe, ByteOffset=null, Key=null) => 0
NtClose(Handle=0x124) => 0
```

Set beside the Linux four lines above, step for step: the failed open returns
`-1 ENOENT` on Linux and `0xC0000034` *with* its Win32 translation `[2 '…']`
on Windows — two error namespaces in one return value; the open yields file
descriptor `3` on Linux and handle `0x124` on Windows; the write is `14` bytes
on Linux and `Length=0xe` on Windows — the same fourteen, one call on each
side for three `fwrite`s; the close is `close(3)` and `NtClose(Handle=0x124)`.
Every difference is the operating system's. That is the comparison the
lecture was built around, and it exists now.

## Writing to a pipe instead of a file — captured 2026-09-20

Lecture 3, section 5. Same binary, same container, the output path is
`/dev/stdout` and stdout is a pipe into `cat`:

```sh
docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c \
  sh -c 'strace -e trace=openat,write,close -o /tmp/t ./iodemo /dev/stdout | cat; cat /tmp/t'
```

The program's four steps, verbatim, after the loader's own lines:

```text
openat(AT_FDCWD, "no-such-file.txt", O_RDONLY) = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "/dev/stdout", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 3
write(3, "one\ntwo\nthree\n", 14)       = 14
close(3)                                = 0
+++ exited with 0 +++
```

Set beside the file run above: the same four calls, the same fourteen bytes
in one `write`, the same descriptor number. Nothing in the program knows it is
talking to a pipe; `cat` on the other end received `one two three`. That is
the point of the section — the file descriptor is the abstraction, not the
file. The prediction to collect before running it (Ondra, 2026-09-20): *which
of the four calls changes when the target is a pipe, and does the byte count
in the `write` change?* — the `openat`, the `write`, the `close`, or nothing.

## Writing to a terminal — captured 2026-09-21

Lecture 3, Part 8, the third destination. Same binary, same container, the
output path is still `/dev/stdout`, but this time stdout is a **terminal**:
`podman run -t` allocates a pseudo-terminal, and nothing follows the program.

```sh
podman run --rm -t --cap-add SYS_PTRACE pb158-iodemo-c \
  sh -c 'strace -e trace=openat,write,close -o /tmp/t ./iodemo /dev/stdout; cat /tmp/t'
```

The program's steps, verbatim, after the loader's own lines:

```text
openat(AT_FDCWD, "no-such-file.txt", O_RDONLY) = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "/dev/stdout", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 3
write(3, "one\n", 4)                    = 4
write(3, "two\n", 4)                    = 4
write(3, "three\n", 6)                  = 6
close(3)                                = 0
+++ exited with 0 +++
```

**Three `write` calls where the file run and the pipe run made one.** The
program is unchanged; the C library changed its mind. Attached to a terminal a
stream is line-buffered, so every `\n` pushes a `write()` out; attached to a
pipe or a regular file it is fully (block) buffered, so the three `fwrite`
calls coalesce into one `write` at `fclose`. The kernel's part of the trace —
the call names, the descriptor number — did not change; only how many times
the same call was made. The prediction to collect first: *one write, or
three — and who decides, the kernel or the C library?*

Try it yourself, one after the other: `./iodemo /dev/stdout` in a terminal,
then `./iodemo /dev/stdout | cat`.

## The same bytes over a TCP socket — netcat on the other side, captured 2026-09-20

Lecture 3, section 5, second leg. `iodemo` cannot open a socket by path — a
socket cannot be reopened through `/dev/stdout` — so the pipe carries the
fourteen bytes to a client `nc`, a listening `nc` receives them, and **both
netcats are traced**: `make container-socket` (the image gains
`netcat-openbsd`). Trimmed to the calls after the loader's own lines:

```text
== client nc (writer)
socket(AF_INET, SOCK_STREAM|SOCK_NONBLOCK, IPPROTO_TCP) = 3
connect(3, {sa_family=AF_INET, sin_port=htons(9000), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 EINPROGRESS (Operation now in progress)
read(0, "one\ntwo\nthree\n", 16384)     = 14
write(3, "one\ntwo\nthree\n", 14)       = 14
read(3, "", 16384)                      = 0
close(3)                                = 0

== listener nc (reader)
socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = 3
bind(3, {sa_family=AF_INET, sin_port=htons(9000), sin_addr=inet_addr("127.0.0.1")}, 16) = 0
listen(3, 1)                            = 0
accept4(3, {sa_family=AF_INET, sin_port=htons(46710), sin_addr=inet_addr("127.0.0.1")}, [128 => 16], SOCK_NONBLOCK) = 4
read(4, "one\ntwo\nthree\n", 16384)     = 14
read(4, "", 16370)                      = 0
close(4)                                = 0
close(3)                                = 0

== received.txt
one
two
three
```

The client reads fourteen bytes from the pipe with `read(0, …)` and puts them
on the TCP socket with **`write(3, …)` — the same call `iodemo` used for the
file and for the pipe**, same fourteen bytes, same descriptor number. The
listener takes them off the wire with **`read(4, …)`**, the call it would use
for a file. What is new is only how the descriptor came to exist: `socket`,
`connect` on one side; `socket`, `bind`, `listen`, `accept4` on the other.
Once it exists, it is a file descriptor, and `read`/`write` do not care.

The prediction to collect first: *the listener receives fourteen bytes from a
TCP socket — which call takes them off the wire: `read`, the same as for a
file, or a socket-specific call?* This netcat used `read` and `write`; a
program may spell them `recv` and `send`, which the manual documents as
equivalent with zero flags (send(2): "With a zero flags argument, send() is
equivalent to write(2)") — the choice is the program's, not the kernel's.
Windows is the contrast on the slide: a socket there is a `SOCKET`, not a
`HANDLE`, and `ReadFile` on it is not the ordinary path.

Not shown: the client's `connect` returned `EINPROGRESS` because this netcat
opens the socket non-blocking and waits for readiness before writing — the
mechanism section 4 is about, visible in passing.


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

---
created: 2026-09-13
tags:
  - talk
  - demo
  - operating-systems
  - tracing
---

# Lecture 3 demos — the Lecture 2 programs, plus whose done it was, and how a program waits

**Section 4 introduces it**: show the source, compile, run. Three `fwrite`
calls, fourteen bytes, **one** `write` in the trace — three source lines, one
system call.

**Section 5 traces it on both platforms.** Because the room met the program in
section 4, every difference between the two traces belongs to the operating
system rather than to an unfamiliar program. No shell command qualifies for
this job: `cat` and `type` are different programs by different authors, and
comparing them would attribute an implementation difference to the platform.

## One folder per program

`nttrace-count.py` (this folder) counts an NtTrace capture per native call —
the Windows parity for `strace -c`, since NtTrace lists and does not count.
Windows demos are captured by Ondra on the x64 tool-chain; each folder's
README has a **Captured** section that says whether the numbers exist yet.
A slide never shows a number that section does not have.

| folder | what | runs on | container |
|---|---|---|---|
| [`scatter/`](scatter/README.md) | `gather.py` / `zerocopy.py` — three `write` calls vs one `writev`; a copy loop vs `sendfile` into a pipe (Lecture 3, Part 9) | Linux (container) | `python:3.12-slim` + strace |
| [`durability/`](durability/README.md) | `save.py` / `watch_dirty.py` — a program says *done*, the kernel writes the bytes later; the four-mode `write`/`fsync` counts (Lecture 3, Part 6). Windows twins: `watch_dirty_win32.py` (PDH counters), `iocost.c` | Linux (container); Windows | `python:3.12-slim` + strace |
| [`waiting/`](waiting/README.md) | `wait_blocking.py` / `wait_epoll.py` — two ways to wait for input that never comes, counted with `strace -c` (Lecture 3, Part 7). Windows twins: `wait_peek*` / `wait_iocp*` in PyWin32 and C | Linux (container); Windows | `python:3.12-slim` + strace |
| [`iodemo-c/`](iodemo-c/README.md) | `iodemo.c` — the program on the slides; `Makefile` (GNU) and `Makefile.msvc` | Linux, Windows | Debian + gcc + strace + ltrace |
| [`iodemo-python/`](iodemo-python/README.md) | `iodemo.py` — the same program one level up, and the one-liner | Linux, Windows | `python:3.12-slim` + strace + ltrace |
| [`destinations-win32/`](destinations-win32/README.md) | `dest.c` / `dest_win32.py` — fourteen bytes to a pipe, to a socket via `send`, and to the same socket via `WriteFile` (Lecture 3, Part 8, Windows half) | Windows only | — |
| `osexit.py` (this folder) | four lines: `print("hello")`, then `os._exit(0)` — run it with stdout on a pipe (`python3 osexit.py | cat`) and with stdout on the terminal, and compare what arrives (Lecture 3, Part 2: what dies with the process) | Linux, Windows | — |
| [`iocount-win32/`](iocount-win32/README.md) | `iocount_win32.py` — the kernel's write count through PyWin32 | Windows only | — |

The three `iodemo*` folders are carried unchanged from Lecture 2 (its slides 33–63 are this lecture's section 2). `iodemo-c/README.md` gains one new capture: the program writing to a pipe (section 5). Each folder's README says how to build, run, trace and count there. The two
Linux folders carry a `Dockerfile` and `make image` / `make container-trace` /
`make container-count` targets, so the Linux half of every demo runs on any
machine with Docker — including the lecturer's — without installing a
compiler or a tracer on the host. The makefiles pass `--cap-add SYS_PTRACE` for
the tracers — not needed on a current Docker, needed on older kernels.

## Why it prints nothing

Deliberate. Console output on Windows travels through the console subsystem,
which is a different path from file I/O, and it would add lines to the trace
that have nothing to do with the lesson. It also drags in line-buffered versus
block-buffered behaviour, which belongs in section 3. The program is silent and
writes to a regular file; the trace does the talking.

A consequence worth saying aloud in the room: **the program reports no error,
and the trace shows one anyway.** That is the whole argument for tracing.

## The matched pair

```sh
strace  -e trace=openat,write,close  ./iodemo iodemo.out
```

```bat
NtTrace -filter NtCreateFile,NtWriteFile,NtClose  iodemo.exe iodemo.out
```

The two invocations are deliberately near-identical in shape, so that nothing
in the output can be blamed on how the tracer was asked.

`NtTrace -filter` takes **substrings of entry-point names**, not categories —
`-category` is a separate option. That is why the author's own published sample
used `-filter File` and matched `NtOpenFile`, `NtWriteFile`,
`NtQueryVolumeInformationFile` and more. Filtering to three names keeps the
loader's own file activity out of the way.

NtTrace needs **no administrator rights**: it is a debugger, not a driver
([project page](https://rogerorr.github.io/NtTrace/), [source](https://github.com/rogerorr/NtTrace)).

## Counting without a tracer

Both `iodemo` programs take `--count` and print the kernel's own count of write
operations for the process — `/proc/self/io` `syscw` on Linux,
`GetProcessIoCounters` → `WriteOperationCount` on Windows. This is the Windows
answer to `strace -c`: NtTrace has no counting summary, and the kernel counted
anyway, for free. The same counters are visible from outside the program in
Process Explorer and Task Manager. Limits and details are in each folder's
README; `iocount-win32/` shows the same call through PyWin32.

## Captured on Windows, 2026-09-15 — `NtTrace64-CMD-ECHO-Output.txt`

Our own NtTrace capture, unfiltered, 275 lines: `NtTrace64.exe` tracing
`cmd.exe /c echo Hello World!` — a 64-bit process on a 2026 Windows, run by
Ondra on an ARM64 machine under the x64 emulation layer (the fourth line loads
`xtajit64se.dll` before `KERNEL32.DLL`). It replaces the borrowed XP-era
sample on the Part V slide. What it is **not**: a trace of `iodemo.exe`. It
traces the shell, so it still shows the *shape* of a Windows trace rather than
the Windows half of the matched pair; `nmake /f Makefile.msvc trace` in
`iodemo-c/` produces that half.

Three lines to read on the slide:

```text
NtOpenKey(KeyHandle=…, DesiredAccess=GENERIC_READ|0x100, ObjectAttributes="\Registry\Machine\SOFTWARE\Microsoft\AppModel\Lookaside\machine") => 0xc0000034 [2 'The system cannot find the file specified.']
NtQueryAttributesFile(ObjectAttributes="\??\C:\WINDOWS\system32\c_852.nls", Attributes=… [ARCHIVE]) => 0
NtWriteFile(FileHandle=0x20c, Event=0, ApcRoutine=null, ApcContext=null, IoStatusBlock=… [0/0xf], Buffer=0x7ff7357a0730, Length=0xf, ByteOffset=null, Key=null) => 0
```

The first is the two error namespaces in one return value: the `NTSTATUS`
`0xC0000034`, then in brackets the Win32 error it maps to, `2`, with its
text. The second is an object-manager path — `\??\C:\…` — that no Win32
program ever types (and `c_852.nls` is the code page of a Czech console). The
third is the one write the shell made: fifteen bytes to handle `0x20c`, which
the preceding `NtQueryVolumeInformationFile` had just identified as a console
device. The traced program's own output, `Hello World!`, appears in the file
one line above it, where the console printed it.

Everything else in the file is a shell starting up: registry probes
(`NtOpenKeyEx`, `NtQueryValueKey`), section mapping for each DLL, a WIL
staging semaphore that does not exist. That volume is itself the lesson from
the Python trace, one operating system over.

## Status

**The Linux traces are captured** — 2026-09-15, in the containers, and
recorded verbatim in each Linux folder's README; `make container-trace`
reproduces them on any machine with Docker. The C program compiles with `-Wall
-Wextra` and no warnings; all three programs write the same 14 bytes.

**Both halves of the matched pair are captured** — Linux on 2026-09-15 in the
container, Windows the same day by Ondra (`iodemo-c/NtTrace64-IODEMO-Output.txt`,
x64 under emulation on an ARM64 host). The four steps line up call for call;
`iodemo-c/README.md` sets them side by side. The `cmd.exe` capture above stays
as the example of a shell's start-up noise and of an object-manager `\??\`
path, which the program's own trace does not show (its opens are relative to a
directory handle).

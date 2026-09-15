---
created: 2026-09-13
tags:
  - talk
  - demo
  - operating-systems
  - tracing
---

# Sections 4 and 5 demo — one program, two jobs

**Section 4 introduces it**: show the source, compile, run. Three `fwrite`
calls, fourteen bytes, **one** `write` in the trace — three source lines, one
system call.

**Section 5 traces it on both platforms.** Because the room met the program in
section 4, every difference between the two traces belongs to the operating
system rather than to an unfamiliar program. No shell command qualifies for
this job: `cat` and `type` are different programs by different authors, and
comparing them would attribute an implementation difference to the platform.

## One folder per program

| folder | what | runs on | container |
|---|---|---|---|
| [`iodemo-c/`](iodemo-c/README.md) | `iodemo.c` — the program on the slides; `Makefile` (GNU) and `Makefile.msvc` | Linux, Windows | Debian + gcc + strace + ltrace |
| [`iodemo-python/`](iodemo-python/README.md) | `iodemo.py` — the same program one level up, and the one-liner | Linux, Windows | `python:3.12-slim` + strace + ltrace |
| [`iocount-win32/`](iocount-win32/README.md) | `iocount_win32.py` — the kernel's write count through PyWin32 | Windows only | — |

Each folder's README says how to build, run, trace and count there. The two
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

## Status

**The Linux traces are captured** — 2026-09-15, in the containers, and
recorded verbatim in each Linux folder's README; `make container-trace`
reproduces them on any machine with Docker. The C program compiles with `-Wall
-Wextra` and no warnings; all three programs write the same 14 bytes.

**No Windows trace of this program is recorded, and none should be invented.**
It must be produced by running `nmake /f Makefile.msvc trace` on a Windows
machine and pasted in as captured. The one published NtTrace sample the vault
holds traces `cmd`, not this program, and is a 32-bit XP-era capture; the deck
says so on the slide that shows it.

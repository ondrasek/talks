---
created: 2026-09-15
tags:
  - talk
  - demo
  - operating-systems
  - tracing
  - python
---

# `iodemo.py` — the same program, one level up

The Python twin of [`../iodemo-c/iodemo.c`](../iodemo-c/README.md): the same
deliberate failure, the same three writes, the same fourteen bytes,
byte-for-byte. The difference the trace shows is the interpreter's own traffic
in front of the four lines that matter, and the absence of a C library buffer
underneath — `FileIO` calls `write()` itself.

## Run and trace

### Linux, natively

```sh
make run        # python3 iodemo.py iodemo.out
make trace      # strace -e trace=openat,write,close python3 iodemo.py iodemo.out
make count      # python3 iodemo.py iodemo.out --count
```

### Linux, in a container

The `Dockerfile` is the official `python:3.12-slim` image plus `strace` and
`ltrace`.

```sh
make image              # docker build -t pb158-iodemo-python .
make container-trace    # docker run --rm --cap-add SYS_PTRACE pb158-iodemo-python
make container-count    # docker run --rm pb158-iodemo-python python3 iodemo.py iodemo.out --count
```

`--cap-add SYS_PTRACE` is belt and braces: Docker drops `CAP_SYS_PTRACE` by
default and, on kernels before 4.8, its default seccomp profile blocks
`ptrace` outright
([Docker: seccomp security profiles](https://docs.docker.com/engine/security/seccomp/)).
A current Docker traces the container's own child without it (verified
2026-09-15), but the flag costs nothing. The `--count` run needs no capability.

The counting summary is worth one run here:

```sh
docker run --rm --cap-add SYS_PTRACE pb158-iodemo-python strace -c python3 iodemo.py iodemo.out
```

### Windows

```bat
python iodemo.py iodemo.out
python iodemo.py iodemo.out --count
NtTrace -filter NtCreateFile,NtWriteFile,NtClose python iodemo.py iodemo.out
```

## Captured in the container, 2026-09-15

Docker 29.7, `python:3.12-slim` (Debian trixie), arm64. The tail of
`make container-trace`, after the interpreter's start-up traffic:

```text
openat(AT_FDCWD, "/demo/iodemo.py", O_RDONLY) = 3
close(3)                                = 0
openat(AT_FDCWD, "no-such-file.txt", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "iodemo.out", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 3
write(3, "one\ntwo\nthree\n", 14)       = 14
close(3)                                = 0
+++ exited with 0 +++
```

`strace -c` for the same run: **4 `write` calls out of 355 system calls**
(45 of them errors — path probes). `make container-count` printed
`write operations counted by the kernel: 10`: one is ours, the rest are the
interpreter starting up, which is why the count is read twice and subtracted
in `../iocount-win32/`.

## What to expect from the trace

**Noise first.** CPython opens dozens of files before it reaches your code —
every import, every path probe — and on Windows it also loads the interpreter
DLL and its dependencies. With the `openat` filter on, the interpreter's
start-up fills the screen before the four lines that matter. That noise is
itself the argument for tracing the C program on the slide: the point of
section 5 is the platform difference, and it should not have to be found in a
haystack. Filter to `write` alone and the one line that matters stands out.

**Then the same four steps** as the C program: the failed open, the open, one
`write` of 14 bytes for three `f.write` calls, the close. No C library buffer
sits under Python — the three writes were collected by `BufferedWriter` and
handed to `write()` directly.

## `--count`

Same flag, same meaning as the C program: the kernel's own count of write
operations for this process — `/proc/self/io` `syscw` on Linux,
`GetProcessIoCounters` through `ctypes` on Windows — printed at the end. The
count covers the whole process, and the interpreter wrote before your first
line ran; compare two runs rather than reading one.

## The one-liner

Same idea again, with no file to keep. Identical quoting works in both `bash`
and `cmd`, because the inner quotes are single and `\n` is not special to
either shell:

```
python -c "f=open('iodemo.out','wb'); f.write(b'one\n'); f.write(b'two\n'); f.write(b'three\n'); f.close()"
```

Verified 2026-09-13 to produce byte-for-byte the same 14-byte file as the C
program and as `iodemo.py`. It **omits the deliberate failure**: an uncaught
exception in a one-liner prints a traceback to the console and puts exactly
the noise back that the silence was protecting. Trace it only as a secondary
slide, and only with the write filter on.

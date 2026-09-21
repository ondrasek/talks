#!/usr/bin/env python3
"""zerocopy.py — move a file into a pipe without the bytes ever entering this process.

    python3 zerocopy.py MODE [SIZE_MIB=4]      MODE = copy | sendfile

WHAT THIS SHOWS
  To move a file into a pipe (or a socket), the obvious loop reads a chunk into
  a buffer and writes it out again. Every byte then crosses into user space and
  back: two copies per chunk, two system calls per chunk. sendfile() hands the
  kernel a source descriptor, a destination descriptor and a length, and the
  kernel moves the bytes itself — from the page cache to the pipe — while this
  process never holds a single one of them. Zero copies through user space.

    copy       read() into a 64 KiB buffer, write() it out, repeat
    sendfile   os.sendfile(pipe, file, offset, remaining), repeat until done

  The other end of the pipe is a child that drains it, so the numbers describe
  the transfer and not a stalled pipe.

WHAT TO LOOK AT
  Under `strace -c` (make count): the copy loop's 64 read + 64 write calls against
  64 sendfile calls and no read/write of the data at all. Each sendfile moved
  64 KiB because that is what the pipe would take at once — the pipe's
  capacity, not sendfile's limit.

WHAT NOT TO CONCLUDE
  At 4 MiB into a pipe the wall-time difference is small and noisy; the honest
  claim is the copies avoided and the calls halved, not a speed-up. Zero-copy
  moves bytes the kernel already has; it cannot help a program that must look
  at the bytes, and it does nothing for durability — the same four levels sit
  below the pipe as below a file.
"""

import os, sys, time

mode = sys.argv[1] if len(sys.argv) > 1 else "copy"
mib = int(sys.argv[2]) if len(sys.argv) > 2 else 4
src = "payload.bin"
with open(src, "wb") as f:
    f.write(b"\0" * (mib * 1024 * 1024))
r, w = os.pipe()
pid = os.fork()
if pid == 0:                       # drain
    os.close(w)
    total = 0
    while True:
        chunk = os.read(r, 1 << 20)
        if not chunk:
            break
        total += len(chunk)
    os._exit(0 if total == mib * 1024 * 1024 else 1)
os.close(r)
fd = os.open(src, os.O_RDONLY)
size = os.fstat(fd).st_size
t0 = time.perf_counter()
if mode == "copy":
    calls = 0
    while True:
        buf = os.read(fd, 1 << 16)          # copy 1: kernel -> this process
        if not buf:
            break
        os.write(w, buf); calls += 2        # copy 2: this process -> kernel; two syscalls per chunk
elif mode == "sendfile":
    calls = 0; off = 0
    while off < size:
        sent = os.sendfile(w, fd, off, size - off)   # the kernel moves the bytes; we never see them
        if sent == 0:
            break
        off += sent; calls += 1
else:
    sys.exit(f"unknown mode {mode!r}")
elapsed = time.perf_counter() - t0
os.close(w); os.close(fd)
_, status = os.waitpid(pid, 0)
print(f"done: mode={mode}, {size // (1024*1024)} MiB, {calls} data syscall(s) in this process, {elapsed*1000:.1f} ms, drain ok={os.waitstatus_to_exitcode(status) == 0}")

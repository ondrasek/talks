#!/usr/bin/env python3
"""save.py — write a hundred records to a file, one of four ways, then say "done".

    python3 save.py MODE [RECORDS=100] [RECORD_BYTES=64] [PATH=saved.bin]

WHAT THIS SHOWS
  Every program that "saves a file" prints something like done and moves on.
  This one lets you choose how hard it tries to get the bytes out of its own
  hands before it says so, and what each choice costs:

    default      open(..., "wb")                  the runtime's buffer, emptied at close():
                                                  a handful of write() calls, then the bytes are
                                                  the KERNEL's — in the page cache, not on the disk
    flush        f.flush() after every record     one write() per record: the bytes reach the
                                                  kernel each time, still not the disk
    fsync        f.flush(); os.fsync()            and the kernel is asked to push them to the
                                                  DEVICE before the call returns — the expensive one
    unbuffered   open(..., "wb", buffering=0)     every f.write() is a write(): same as flush

WHAT TO LOOK AT
  Under `strace -c` (make count): the number of write() and fsync() calls per
  mode, and the wall time. flush and fsync make the SAME 101 write() calls;
  fsync costs sixty times more, because the cost is the waiting for the device,
  not the crossing. Then watch_dirty.py, which runs this program in default
  mode and shows the bytes leaving the page cache seconds AFTER "done".

WHY IT MATTERS
  "done" here is the program's done. Lecture 3 asks whose done it was.
"""

import os, sys, time

mode = sys.argv[1] if len(sys.argv) > 1 else "default"
records = int(sys.argv[2]) if len(sys.argv) > 2 else 100
record_bytes = int(sys.argv[3]) if len(sys.argv) > 3 else 64
path = sys.argv[4] if len(sys.argv) > 4 else "saved.bin"

if mode not in ("default", "flush", "fsync", "unbuffered"):
    sys.exit(f"unknown mode {mode!r}")

record = (b"record " + b"x" * record_bytes)[:record_bytes - 1] + b"\n"
t0 = time.perf_counter()
# buffering=0 means no user-space buffer at all: every f.write() is a write() syscall.
# -1 (the default) means Python's BufferedWriter collects records and writes them in blocks.
with open(path, "wb", buffering=0 if mode == "unbuffered" else -1) as f:
    for _ in range(records):
        f.write(record)                # level 1 of the buffer stack: the runtime's buffer
        if mode in ("flush", "fsync"):
            f.flush()                  # level 1 -> level 3: write() into the kernel's page cache
        if mode == "fsync":
            os.fsync(f.fileno())       # level 3 -> level 4: ask the kernel to push it to the device, and wait
elapsed = time.perf_counter() - t0
# This line is the PROGRAM's "done". The kernel has not necessarily written anything yet.
print(f"done: {records} records x {record_bytes} B, mode={mode}, {elapsed*1000:.1f} ms")

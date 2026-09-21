#!/usr/bin/env python3
"""gather.py — three buffers, one message: three write() calls, or one writev().

    python3 gather.py MODE [PATH=gathered.bin]      MODE = separate | gather

WHAT THIS SHOWS
  A message that lives in three places in your program — a header, a body, a
  trailer — has to reach the file as one message. Two ways:

    separate   os.write() three times: three crossings into the kernel, and
               another writer on the same file can land its bytes BETWEEN yours.
    gather     os.writev() once with a list of three buffers: ONE crossing; the
               kernel GATHERS the pieces itself, and POSIX promises the writev is
               atomic against other writers on the descriptor. Nothing is copied
               in your program to make it one message — the buffers stay where
               they are. readv() is the mirror image: one crossing SCATTERS into
               several buffers.

WHAT TO LOOK AT
  Under strace (make trace): three write() lines against ONE writev() line whose
  return value is the whole message, 57 bytes. Same bytes on disk either way.

WHY IT MATTERS
  Same four-level buffer stack, one fewer trip through it — and a whole log line
  that cannot be interleaved. This is the ordinary, unglamorous use of
  scatter/gather (Valkey does it for every reply).
"""

import os, sys

mode = sys.argv[1] if len(sys.argv) > 1 else "separate"
path = sys.argv[2] if len(sys.argv) > 2 else "gathered.bin"
header = b"HEADER  "
body = b"body " * 8
trailer = b" TRAILER\n"
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
if mode == "separate":
    n = os.write(fd, header) + os.write(fd, body) + os.write(fd, trailer)   # three crossings
elif mode == "gather":
    n = os.writev(fd, [header, body, trailer])                              # ONE crossing, three buffers, atomic
else:
    sys.exit(f"unknown mode {mode!r}")
os.close(fd)
print(f"done: mode={mode}, {n} bytes, 3 buffers")

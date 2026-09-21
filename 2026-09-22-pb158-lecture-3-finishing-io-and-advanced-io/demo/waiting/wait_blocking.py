"""wait_blocking.py — a hundred pipes nobody writes to, asked in turn. This is POLLING.

    python3 wait_blocking.py [pipes=100] [seconds=2]

WHAT THIS SHOWS
  Nothing ever arrives on any of the hundred pipes, and the program still spends
  the whole two seconds asking: read() on pipe 1, pipe 2, ... pipe 100, and
  again, and again. Each read() is non-blocking, so it returns at once with
  EAGAIN ("nothing yet") — one trip into the kernel that learns nothing.
  Compare wait_epoll.py, which asks once.

WHAT TO LOOK AT
  Under `strace -c` (make count): the number of read() calls and how many of
  them are errors. On the container: 28,017 calls, 28,000 EAGAIN, in two
  seconds. That number is a RATE (twenty seconds would be ten times more) and a
  FLOOR (the tracer slows the loop; untraced, a laptop asked 1.3 million times
  a second). Count under the tracer, time without it.

WHY IT MATTERS
  This is how a program waits when it does not know how to wait: it asks, and
  pays for every ask while nothing is happening. Kegel's C10K problem was
  exactly this cost, multiplied by ten thousand connections.
"""

import os
import sys
import time

pipes = int(sys.argv[1]) if len(sys.argv) > 1 else 100
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

readers = []
for _ in range(pipes):
    r, w = os.pipe()
    os.set_blocking(r, False)   # non-blocking: read() returns at once with EAGAIN instead of waiting
    readers.append(r)

deadline = time.monotonic() + seconds
asked = 0
while time.monotonic() < deadline:
    for r in readers:
        try:
            os.read(r, 1)        # THE ASK: one system call per pipe per round; nothing is there
        except BlockingIOError:  # EAGAIN — "nothing yet". Not a fault: the kernel's honest answer
            pass
        asked += 1
print(f"asked {asked} times across {pipes} pipes in {seconds:.0f}s; nothing arrived")

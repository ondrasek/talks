"""wait_epoll.py — a hundred pipes nobody writes to, ONE wait. This is READINESS.

    python3 wait_epoll.py [pipes=100] [seconds=2]

WHAT THIS SHOWS
  The same hundred pipes and the same silence as wait_blocking.py, but the
  program does not ask. It tells the kernel ONCE which pipes it cares about
  (epoll_ctl, a hundred times, at start-up) and then makes ONE call that sleeps
  until any of them has data or the timeout passes (epoll_pwait). Nothing ever
  arrives, so that one sleeping call is the entire cost of waiting on a hundred
  pipes for two seconds. The kernel says "you may read now" — readiness — and
  the program would then do the read itself. Here it is never told.

WHAT TO LOOK AT
  Under `strace -c` (make count): 100 epoll_ctl (paid once, however long the
  program then waits) and ONE epoll_pwait, against wait_blocking.py's 28,017
  reads in the same two seconds. The polling count is a rate; this one is a
  constant.

WHY IT MATTERS
  This is how a server waits on ten thousand idle connections without spinning:
  Kegel's C10K answer, and the mechanism behind every event loop you will meet.
  Windows' native answer is different in kind — completion, not readiness — see
  wait_iocp.c / wait_iocp_win32.py.

  The `selectors` module picks the platform's readiness mechanism: epoll on
  Linux, kqueue on macOS. The lecture's numbers come from the Linux container.
"""

import os
import selectors
import sys
import time

pipes = int(sys.argv[1]) if len(sys.argv) > 1 else 100
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

sel = selectors.DefaultSelector()           # epoll on Linux; the interest set lives in the kernel
for _ in range(pipes):
    r, w = os.pipe()
    sel.register(r, selectors.EVENT_READ)   # epoll_ctl: tell the kernel ONCE that this pipe matters

deadline = time.monotonic() + seconds
waits = 0
while time.monotonic() < deadline:
    ready = sel.select(timeout=max(0.0, deadline - time.monotonic()))  # epoll_pwait: THE ONE CALL — sleeps until told or timed out
    waits += 1
    for key, _ in ready:              # readiness: the kernel said "you may read"; the program still does the read
        os.read(key.fd, 1)            # (never reached here — nobody writes)
print(f"waited {waits} time(s) across {pipes} pipes in {seconds:.0f}s; nothing arrived ({type(sel).__name__})")

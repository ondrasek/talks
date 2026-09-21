#!/usr/bin/env python3
"""wait_peek_win32.py — a hundred pipes nobody writes to, asked in turn. POLLING, on Windows.

    python wait_peek_win32.py [PIPES=100] [SECS=2]        (Windows, PyWin32)

WHAT THIS SHOWS
  The Windows twin of wait_blocking.py. Nothing ever arrives, and the program
  still spends the whole two seconds asking every pipe in turn — PeekNamedPipe,
  round after round. Every ask is a trip into the kernel that learns nothing.
  Compare wait_iocp_win32.py, which asks once.

WHAT TO LOOK AT
  1. The number of PeekNamedPipe calls in two seconds. It is a RATE: twenty
     seconds would be ten times more, for zero bytes.
  2. The "kernel counted" line — the kernel's own accounting of this process
     (GetProcessIoCounters, the counter Lecture 2 used) shows the peeks as OTHER
     operations.
  3. Under NtTrace64 (nmake trace-py) each PeekNamedPipe is THREE native calls:
     NtCreateEvent, NtFsControlFile(FSCTL_PIPE_PEEK), NtClose. Count under the
     tracer, time without it.

WHY IT MATTERS
  This is how a program waits when it does not know how to wait: it asks, and
  pays for every ask while nothing is happening.
"""
import sys, time
import win32api, win32file, win32pipe, win32con, win32process

pipes = int(sys.argv[1]) if len(sys.argv) > 1 else 100
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

def io_counters():          # the kernel's own per-process accounting
    return win32process.GetProcessIoCounters(win32api.GetCurrentProcess())
def io_delta(what, before):
    now = io_counters()
    print(f"{what}: kernel counted READ ops +{now['ReadOperationCount'] - before['ReadOperationCount']}, "
          f"OTHER ops +{now['OtherOperationCount'] - before['OtherOperationCount']}")

# A hundred named pipes, each with a CONNECTED client that never writes.
servers, clients = [], []
for i in range(pipes):
    name = rf"\\.\pipe\pb158-peek-{i}"
    s = win32pipe.CreateNamedPipe(name, win32pipe.PIPE_ACCESS_INBOUND,
                                  win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT, 1, 4096, 4096, 0, None)
    c = win32file.CreateFile(name, win32con.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
    win32pipe.ConnectNamedPipe(s, None)     # client already there: returns at once
    servers.append(s); clients.append(c)

io0 = io_counters()
peeks = 0
deadline = time.perf_counter() + secs
# THE LOOP THE LECTURE IS ABOUT: ask every pipe, round after round.
while time.perf_counter() < deadline:
    for s in servers:
        _, available, _ = win32pipe.PeekNamedPipe(s, 0)   # one trip into the kernel, for nothing
        peeks += 1
        if available:
            raise SystemExit("someone wrote to a pipe — the demo assumes nobody does")
print(f"done: {pipes} pipes, {secs:.0f}s, {peeks} PeekNamedPipe calls, 0 bytes received")
io_delta("while waiting", io0)
for h in servers + clients:
    win32file.CloseHandle(h)

---
created: 2026-09-20
tags:
  - talk
  - demo
  - operating-systems
  - io
---

# Waiting for input that never comes — two ways, counted

Section 4 of Lecture 3: *readiness versus completion*. Both programs create a
hundred pipes that nobody ever writes to and wait two seconds. They differ only
in **how they wait**, and the tracer counts the difference.

| program | how it waits | what the kernel is asked |
|---|---|---|
| `wait_blocking.py` | asks every pipe in turn, non-blocking, round after round | one `read` per pipe per round — polling |
| `wait_epoll.py` | registers every pipe once, then one call that sleeps until any is readable or the timeout passes | `epoll_ctl` × 100 once, then `epoll_pwait` × 1 |

The `selectors` module picks the platform's readiness mechanism — **epoll on
Linux**, kqueue on macOS — which is why the counts must come from the Linux
container, not from the lecturer's laptop.

## Predict before you run

Write two numbers down: how many system calls each program makes in two
seconds while nothing arrives. Then run `make container-count`.

## Captured in the container, 2026-09-20

`python:3.12-slim` (Debian trixie), 100 pipes, 2 seconds, `strace -c -f`:

```text
wait_blocking.py
% time     seconds  usecs/call     calls    errors syscall
 97.75    0.169636           6     28017     28000 read
100.00    0.173535           6     28549     28043 total

wait_epoll.py
% time     seconds  usecs/call     calls    errors syscall
 16.97    0.000837           8       100           epoll_ctl
  1.97    0.000097          97         1           epoll_pwait
100.00    0.004932           6       724        55 total
```

**28,017 `read` calls, 28,000 of them failing with `EAGAIN`, against one
`epoll_pwait` that slept for two seconds.** The hundred `epoll_ctl` calls are
the registration — paid once, however long the program then waits. Everything
else in both totals is the interpreter starting up (the same ~700 calls L2's
Python trace showed).

Two things the numbers say, and one they do not. The blocking program's count
is a *rate*: run it for twenty seconds and it makes ten times as many calls,
all to learn nothing. The epoll program's count is a *constant*. And the
tracer slowed the polling loop — without `strace` it asks far more often (the
laptop, untraced, asked 1.3 million times in one second) — so the 28,000 is a
floor, not the true rate; "count under the tracer, time without it", as L2
said.

## Readiness, not completion — and the Windows pair that shows completion

Both Linux programs use *readiness*: the kernel says "you may read now", and
the program then reads. Windows' native model is *completion*: the program
hands the kernel a buffer and is told "I have read for you" — overlapped I/O
and I/O completion ports. Ondra, 2026-09-20: this gets a traced pair, not a
slide of documentation.

| file | Linux twin | how it waits | what NtTrace should show |
|---|---|---|---|
| `wait_peek_win32.py` (PyWin32) · `wait_peek.c` | `wait_blocking.py` | a hundred named pipes with connected clients that never write; `PeekNamedPipe` on each, round after round — polling | one `NtFsControlFile` (`FSCTL_PIPE_PEEK`) per peek: thousands |
| `wait_iocp_win32.py` (PyWin32) · `wait_iocp.c` | `wait_epoll.py` | one overlapped `ReadFile` posted per pipe, all bound to one completion port with `CreateIoCompletionPort`, then **one** `GetQueuedCompletionStatus` that sleeps to its timeout — completion | a hundred `NtReadFile` submissions, then one `NtRemoveIoCompletionEx` that sleeps the whole two seconds; `CancelIoEx` on cleanup |
| `Makefile.msvc` | `Makefile` | `nmake /f Makefile.msvc trace` / `trace-py` | both captured and counted with `../nttrace-count.py` |

The tell the lecture teaches, in the trace: many failed asks is polling, one
sleeping call is readiness, **no reads of your own but completions is
completion** — here the reads were submitted up front and the kernel owns the
hundred buffers while nothing happens. The readiness note's own NtTrace
sample shows the shape: the byte count arrives on the dequeue,
`NtRemoveIoCompletion(… Information=…)`, not on the submission.

### Captured — 2026-09-20, Ondra's Windows 11 VM (build 26200, ARM64), NtTrace64 over SSH

Untraced, the C pair, a hundred pipes, two seconds — with the kernel's own
per-process accounting (`GetProcessIoCounters`) printed for the waiting phase:

```text
done: 100 pipes, 2s, 359200 PeekNamedPipe calls, 0 bytes received
while waiting: kernel counted READ ops +0, OTHER ops +359200
done: 100 pipes, one GetQueuedCompletionStatus slept 2.00s, 0 completions, 0 bytes
while waiting: kernel counted READ ops +0, OTHER ops +0
```

The kernel booked every peek as an "other" operation — 359,200 of them, one per
ask — and booked **nothing** for the completion-port program while it waited,
because it did nothing. The PyWin32 pair prints the same lines (261,700 peeks
against 0). That is the point, on the console; the traces below add the call
names.

Traced (`NtTrace64-WAIT-PEEK.txt`, `NtTrace64-WAIT-IOCP.txt`; counted with `../nttrace-count.py`):

```text
== wait_peek.exe   8153 native calls      == wait_iocp.exe    956 native calls
   2725  NtClose                             226  NtClose
   2600  NtFsControlFile  (100 errors)       104  NtCreateFile
   2500  NtCreateEvent                       100  NtCreateNamedPipeFile
    104  NtCreateFile                        100  NtFsControlFile  (100 errors)
    100  NtCreateNamedPipeFile                100  NtSetInformationFile
                                             100  NtReadFile
                                             100  NtCancelIoFileEx
                                               1  NtCreateIoCompletion
                                               1  NtRemoveIoCompletion  => 0x102 (STATUS_TIMEOUT)
done: 100 pipes, 2s, 2500 PeekNamedPipe calls          done: one GetQueuedCompletionStatus slept 2.00s
```

**Polling:** 2,500 peeks in two seconds under the tracer (330,100 untraced —
the tracer slowed each peek a hundredfold; count traced, time untraced), and
each `PeekNamedPipe` is **three** native calls: `NtCreateEvent`,
`NtFsControlFile` (`FSCTL_PIPE_PEEK`), `NtClose`. 7,500 crossings to learn
nothing. **Completion:** 100 `NtReadFile` submissions up front (the kernel
now owns the hundred buffers), 100 `NtSetInformationFile` binding each pipe to
the port, one `NtRemoveIoCompletion` that slept the whole two seconds and
returned `STATUS_TIMEOUT`, then 100 `NtCancelIoFileEx` on the way out. The
hundred "errors" on `NtFsControlFile` in both traces are the
`ConnectNamedPipe` calls returning `STATUS_PIPE_CONNECTED` — an informational
status, not a failure.

**The PyWin32 pair, traced** (`NtTrace64-WAIT-PEEK-PY.txt`,
`NtTrace64-WAIT-IOCP-PY.txt`, Program Files Python 3.14):

```text
== wait_peek_win32.py  6187 native calls     == wait_iocp_win32.py  1984 native calls
   1893  NtClose                                309  NtClose
   1700  NtFsControlFile (100 errors)           153  NtReadFile   (100 are the pipes; the rest the interpreter's files)
   1611  NtCreateEvent                          141  NtSetInformationFile
done: 1600 PeekNamedPipe calls                  100  NtFsControlFile (100 errors)
                                                100  NtCancelIoFile
                                                  1  NtRemoveIoCompletion
                                               done: one GetQueuedCompletionStatus slept 2.01s
```

Same shape as the C pair, one layer up: every `PeekNamedPipe` is again
`NtCreateEvent` + `NtFsControlFile` + `NtClose`, and the completion port is
again a hundred submissions and one dequeue. The interpreter's own file reads
show up as extra `NtReadFile` and `NtSetInformationFile` — the same start-up
noise Lecture 2's Python trace carried, and the reason to compare two runs
rather than trust one.

`WSAPoll` is not in this folder on purpose: it is readiness-shaped and would
prove the wrong thing about the platform.

## Run

```sh
make run              # both programs, natively (kqueue on macOS — the counts differ)
make count            # both under strace -c (Linux only)
make container-count  # the Linux counts above, on any machine with Docker

make win-build        # the Windows twins, from macOS over SSH (../win.sh)
make win-run          # wait_peek.exe and wait_iocp.exe, untraced (time these)
make win-count        # both under NtTrace64, counted like strace -c (count these) — the captures come back too
make win-trace-py     # the PyWin32 pair, the same way
```

On the Windows machine itself: `nmake /f Makefile.msvc run`, `nmake /f
Makefile.msvc count` (or `count-py`). Count traced, time untraced — the
tracer slows each peek a hundredfold, which is the whole point of the pair of
numbers on the slide.

#!/usr/bin/env python3
"""wait_iocp_win32.py — a hundred pipes nobody writes to, ONE wait. COMPLETION, on Windows.

    python wait_iocp_win32.py [PIPES=100] [SECS=2]        (Windows, PyWin32)

WHAT THIS SHOWS
  The Windows twin of wait_epoll.py — but a different MODEL. epoll is READINESS:
  the kernel says "you may read now" and the program then reads. Windows'
  native model is COMPLETION: hand the kernel a buffer up front ("read into this
  when something arrives"), bind the handle to an I/O completion port, and block
  ONCE in GetQueuedCompletionStatus until the kernel says "done, I read it for
  you". Nothing arrives here, so the one wait sleeps to its timeout — and that
  single call is the whole cost of waiting on a hundred pipes.

WHAT TO LOOK AT
  1. "one GetQueuedCompletionStatus slept 2.00s" against wait_peek_win32.py's
     hundreds of thousands of peeks.
  2. The "kernel counted" line: almost nothing, because the program did nothing.
  3. Under NtTrace64 (nmake trace-py): 100 NtReadFile SUBMISSIONS before the
     wait — the kernel now owns the hundred buffers — one NtRemoveIoCompletion
     returning STATUS_TIMEOUT, then the cancels. "No reads of your own, but
     completions" is the tell for this model.

WHY IT MATTERS
  Who owns the buffer while waiting is the real difference between the two
  models (Part 7): here the kernel does, so the buffer must exist before the
  data does and must not be touched until the completion arrives.
"""
import sys, time
import pywintypes, win32api, win32file, win32pipe, win32con, win32process, winerror

pipes = int(sys.argv[1]) if len(sys.argv) > 1 else 100
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

def io_counters():          # the kernel's own per-process accounting
    return win32process.GetProcessIoCounters(win32api.GetCurrentProcess())
def io_delta(what, before):
    now = io_counters()
    print(f"{what}: kernel counted READ ops +{now['ReadOperationCount'] - before['ReadOperationCount']}, "
          f"OTHER ops +{now['OtherOperationCount'] - before['OtherOperationCount']}")

# ONE completion port; every pipe's completions will be queued here.
port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 0, 0)
servers, clients, pending = [], [], []
for i in range(pipes):
    name = rf"\\.\pipe\pb158-iocp-{i}"
    # FILE_FLAG_OVERLAPPED: this handle may have operations in flight.
    s = win32pipe.CreateNamedPipe(name, win32pipe.PIPE_ACCESS_INBOUND | win32file.FILE_FLAG_OVERLAPPED,
                                  win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT, 1, 4096, 4096, 0, None)
    c = win32file.CreateFile(name, win32con.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
    win32pipe.ConnectNamedPipe(s, None)
    win32file.CreateIoCompletionPort(s, port, i, 0)       # bind: completions for this pipe go to the port, tagged i
    ov = pywintypes.OVERLAPPED()                          # the kernel's bookmark for this outstanding read
    buf = win32file.AllocateReadBuffer(64)                # the buffer we are about to hand over
    rc, _ = win32file.ReadFile(s, buf, ov)                # SUBMIT: cannot complete yet, so ERROR_IO_PENDING;
    assert rc == winerror.ERROR_IO_PENDING, f"read completed at once on pipe {i}"   # the kernel now owns buf
    servers.append(s); clients.append(c); pending.append((ov, buf))   # keep both alive until cancelled

io0 = io_counters()
t0 = time.perf_counter()
# THE ONE CALL THE LECTURE IS ABOUT: sleep until any read completes or the timeout passes.
rc, nbytes, key, ov = win32file.GetQueuedCompletionStatus(port, int(secs * 1000))
waited = time.perf_counter() - t0
if rc == winerror.WAIT_TIMEOUT:
    print(f"done: {pipes} pipes, one GetQueuedCompletionStatus slept {waited:.2f}s, 0 completions, 0 bytes")
else:
    print(f"unexpected completion: key={key} bytes={nbytes} rc={rc}")
io_delta("while waiting", io0)
for s in servers:
    win32file.CancelIo(s)          # take the buffers back before closing anything
for h in servers + clients:
    win32file.CloseHandle(h)
win32file.CloseHandle(port)

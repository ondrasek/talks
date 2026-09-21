#!/usr/bin/env python3
"""dest_win32.py — the same fourteen bytes to three destinations, on Windows, from Python.

    python dest_win32.py        (Windows; PyWin32 for the counters and the third leg)

WHAT THIS SHOWS
  On Linux (Part 8, iodemo) the destination did not change the trace: file, pipe
  and socket were all one write(3, ...). Windows is the contrast. The same bytes
  go three ways, and the KERNEL'S OWN ACCOUNTING says which road each took:

    leg 1  os.write to a pipe                      -> a WRITE operation   (NtWriteFile)
    leg 2  socket.send                             -> NOT COUNTED AT ALL   (NtDeviceIoControlFile,
                                                      code 0x1201f = IOCTL_AFD_SEND into afd.sys, on a
                                                      fast I/O path the I/O manager never books)
    leg 3  win32file.WriteFile on the SAME socket  -> a WRITE operation   (NtWriteFile again)

  The API you pick changes the native call; the kernel object underneath is one
  file object either way (a socket is a file under \\Device\\Afd).

WHAT TO LOOK AT
  The "kernel counted" line after each leg. Measured: leg 1 WRITE +1; leg 2
  nothing at all (WRITE +0, OTHER +0 — socket set-up did register as OTHER
  operations, the send did not); leg 3 WRITE +1. NtTrace64 (nmake trace-py)
  shows the call the send did make.

ONE MORE LESSON
  A plain WriteFile on the socket fails with ERROR_INVALID_PARAMETER (87):
  Winsock sockets are overlapped handles, so the file API on a socket is the
  completion model whether you asked for it or not. Leg 3 hands it an
  OVERLAPPED and waits.
"""
import os, socket
import pywintypes, win32api, win32event, win32file, win32process

MSG = b"one\ntwo\nthree\n"   # 14 bytes, exactly what iodemo writes

# The kernel's per-process I/O accounting — the counter Lecture 2's iocount read.
# Snapshot before a leg, print the difference after: what did the kernel think
# just happened?
_prev = win32process.GetProcessIoCounters(win32api.GetCurrentProcess())
def kernel_counted(leg):
    global _prev
    now = win32process.GetProcessIoCounters(win32api.GetCurrentProcess())
    print(f"  {leg:<22} kernel counted: WRITE ops +{now['WriteOperationCount'] - _prev['WriteOperationCount']}"
          f"   READ ops +{now['ReadOperationCount'] - _prev['ReadOperationCount']}"
          f"   OTHER ops +{now['OtherOperationCount'] - _prev['OtherOperationCount']}")
    _prev = now

# ---- leg 1: a pipe, through the file API -----------------------------------
r, w = os.pipe()                       # a CRT descriptor pair over a Win32 anonymous pipe
kernel_counted("(pipe created)")
os.write(w, MSG)                       # one write operation, one NtWriteFile
kernel_counted("1 pipe, os.write")
print(f"pipe:              os.write wrote 14, os.read got {len(os.read(r, 64))}\n")
os.close(r); os.close(w)

# ---- leg 2: a TCP socket, through Winsock ----------------------------------
# Listener, client and accepted peer all in this process, on loopback.
ls = socket.socket(); ls.bind(("127.0.0.1", 0)); ls.listen(1)
cs = socket.create_connection(ls.getsockname())
ps, _ = ls.accept()
kernel_counted("(socket set up)")
sent = cs.send(MSG)                    # Winsock -> afd.sys by device control on a fast path: not booked as I/O at all
kernel_counted("2 socket, send")
print(f"socket, send():    send wrote {sent}, recv got {len(ps.recv(64))}\n")

# ---- leg 3: the SAME socket, through the file API --------------------------
# A SOCKET is a kernel file handle underneath, so WriteFile accepts it — as an
# overlapped handle, so we supply an OVERLAPPED and wait for the result.
ov = pywintypes.OVERLAPPED(); ov.hEvent = win32event.CreateEvent(None, True, False, None)
kernel_counted("(recv done)")
rc, _ = win32file.WriteFile(cs.fileno(), MSG, ov)
n = win32file.GetOverlappedResult(cs.fileno(), ov, True)
kernel_counted("3 socket, WriteFile")
print(f"socket, WriteFile: WriteFile wrote {n}, recv got {len(ps.recv(64))}")
for s in (cs, ps, ls):
    s.close()

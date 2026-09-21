---
created: 2026-09-20
tags:
  - talk
  - demo
  - operating-systems
  - windows
  - networking
---

# Three destinations on Windows — where the trace *does* change

Part 8 of Lecture 3, the Windows half. On Linux the destination did not change
the trace: `iodemo` writing to a file, to a pipe and, through netcat, to a
socket made the same `write(3, …)` call every time. Windows is the contrast.
The same fourteen bytes, `one\ntwo\nthree\n`, go three ways in one process:

| leg | API | what NtTrace should show | why |
|---|---|---|---|
| 1 | `WriteFile` to an anonymous pipe | `NtWriteFile` | a pipe is a file object; the file API is the native path |
| 2 | `send()` on a loopback TCP socket | `NtDeviceIoControlFile` with an AFD send control code | Winsock talks to `afd.sys` through device control, not through the read/write path |
| 3 | `WriteFile` on **the same socket**, cast to `HANDLE` | `NtWriteFile` | the socket is "merely a file under a dedicated device, `\Device\Afd`", so the file API works on it |

So on Windows the *API you pick* changes the native call, and the *kernel
object* is a file object either way. Linux hides the destination behind one
call; Windows shows it at the API and hides it in the kernel. Same fourteen
bytes, opposite places to look.

| file | what |
|---|---|
| `dest.c` | the three legs in C/Win32; listener, client and accepted peer all in-process on loopback |
| `dest_win32.py` | the same from Python: `os.write` to a pipe, `socket.send`, then `win32file.WriteFile` on `sock.fileno()` |
| `Makefile.msvc` | `nmake /f Makefile.msvc trace` / `trace-py` — builds, traces with NtTrace64 filtered to the three calls, counts with `../nttrace-count.py` |

## Predict before you run

Three legs, fourteen bytes each. **Which native call does each one make — and
is it the same call for leg 1 and leg 3?** Write it down.

## Captured — 2026-09-20, Ondra's Windows 11 VM (build 26200, ARM64), NtTrace64 over SSH

`dest.exe` (x64, MSVC 19.51), filtered to `NtCreateFile,NtWriteFile,NtDeviceIoControlFile`;
the three legs and the peer's receives, trimmed to handle, control code, length,
status and result (full capture: `NtTrace64-DEST.txt`):

```text
NtWriteFile(FileHandle=0x118, Length=0xe, IoStatusBlock [0/0xe]) => 0
NtDeviceIoControlFile(FileHandle=0x138, IoControlCode=0x0001201f, Length=0x18, IoStatusBlock [0/0xe]) => 0
NtDeviceIoControlFile(FileHandle=0x134, IoControlCode=0x00012017, Length=0x18, IoStatusBlock [0/0xe]) => 0
NtWriteFile(FileHandle=0x138, Length=0xe) => 0
NtDeviceIoControlFile(FileHandle=0x134, IoControlCode=0x00012017, Length=0x18, IoStatusBlock [0/0xe]) => 0
pipe:              WriteFile wrote 14, ReadFile got 14
socket, send():    send wrote 14, recv got 14
socket, WriteFile: WriteFile wrote 14, recv got 14
```

`dest_win32.py` under the Program Files Python 3.14 (ARM64) with PyWin32,
same filter (full capture: `NtTrace64-DEST-PY.txt`):

```text
NtWriteFile(FileHandle=0x264, Length=0xe, IoStatusBlock [0/0xe]) => 0
NtDeviceIoControlFile(FileHandle=0x268, IoControlCode=0x0001201f, Length=0x18, IoStatusBlock [0/0xe]) => 0
NtDeviceIoControlFile(FileHandle=0x26c, IoControlCode=0x00012017, Length=0x18, IoStatusBlock [0/0xe]) => 0
NtWriteFile(FileHandle=0x268, Length=0xe) => 0
NtDeviceIoControlFile(FileHandle=0x26c, IoControlCode=0x00012017, Length=0x18, IoStatusBlock [0/0xe]) => 0
pipe:              os.write wrote 14, os.read got 14
socket, send():    send wrote 14, recv got 14
socket, WriteFile: WriteFile wrote 14, recv got 14
```

**Read across both:**

| leg | native call | evidence |
|---|---|---|
| 1 · `WriteFile` / `os.write` to the pipe | **`NtWriteFile`**, `Length=0xe` | the pipe handle (`0x118` / `0x264`), status `[0/0xe]`: 14 bytes |
| 2 · `send()` / `socket.send` | **`NtDeviceIoControlFile`**, `IoControlCode=0x0001201f` | `0x1201f` is `IOCTL_AFD_SEND` (Lewczak, *Under the hood of AFD.sys*, part 3); status `[0/0xe]`: 14 bytes accepted by `afd.sys`. The peer's `recv` is the matching `0x00012017`, `AFD_RECEIVE`, the code the readiness note's own NtTrace sample decodes |
| 3 · `WriteFile` on the socket | **`NtWriteFile`**, `Length=0xe`, **same handle as leg 2** (`0x138` / `0x268`) | the file API reached the socket's file object directly; `Event=` and `ByteOffset=` are set because the handle is overlapped and the program supplied an `OVERLAPPED` |

So: on Windows the *API* changes the native call — `send` is device control into
`afd.sys`, `WriteFile` is a file write — and the *object* underneath is one file
handle either way. Linux showed the mirror image in Part 8: one call, three
destinations, nothing visible. NtTrace does not name the AFD codes (its cfg has no
AFD table), which is why the decoding above cites the sources rather than the
tool.

**The kernel's own accounting, on the console** (both programs print
`GetProcessIoCounters` deltas after each leg — Ondra, 2026-09-20: "if I cannot
see the point, students won't"):

```text
  1 pipe, WriteFile      kernel counted: WRITE ops +1   READ ops +0   OTHER ops +0
  2 socket, send()       kernel counted: WRITE ops +0   READ ops +0   OTHER ops +0
  3 socket, WriteFile    kernel counted: WRITE ops +1   READ ops +0   OTHER ops +0
```

Leg 2 left **no mark at all**. Socket set-up did (the PyWin32 run shows
`OTHER ops +115` for `socket`/`bind`/`listen`/`connect`/`accept`), but the
`send` itself was not booked as I/O by the process accounting — which matches
the AFD write-up's account of `IOCTL_AFD_SEND` travelling a *Fast I/O* path
that never builds an I/O request packet. So the console alone says: two
`WriteFile` calls to two different objects are booked identically, and the
Winsock call on the same socket is invisible to the counter that Lecture 2
taught the room to trust. The trace below says which call it made instead.

**Counts** (`../nttrace-count.py`): C — 3 `NtWriteFile`, 24 `NtDeviceIoControlFile`,
7 `NtCreateFile`; Python — 3 `NtWriteFile`, 33 `NtDeviceIoControlFile`. Of the
three `NtWriteFile` calls in each, the third is the program's own `printf`/`print`
to the console; the other device-control calls are Winsock's socket creation,
bind, listen, connect and accept — every one of them `afd.sys` device control,
which is the point of leg 2 made twenty times over.

**The lesson from the first run stays:** a plain `WriteFile((HANDLE)sock, …, NULL)`
fails with `ERROR_INVALID_PARAMETER` (87), because Winsock sockets are overlapped
handles by default; both programs now hand it an `OVERLAPPED` and wait.

## Sources the programs rest on

- the sockets note's record that a socket handle "can optionally be a file
  handle" usable with `ReadFile`/`WriteFile`, with the performance caveat for
  non-IFS providers;
- the same note's account of `afd.sys`: Winsock's send path is
  `NtDeviceIoControlFile` with AFD control codes;
- the readiness note's NtTrace sample of `NtDeviceIoControlFile(…
  [AFD_RECEIVE] …)`, which shows the decoder names the AFD codes.

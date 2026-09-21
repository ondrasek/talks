---
created: 2026-09-20
tags:
  - talk
  - demo
  - operating-systems
  - io
---

# Close it twice — what the second close hits

Part 5 of Lecture 3, behind the carried slide *Never retry a failed close*.
One descriptor, two `close` calls; the second one is what a retry would do.

| file | platform | what |
|---|---|---|
| `close_twice.py` | Linux, macOS, Windows | open, write 14 bytes, `os.close`, `os.close` again |
| `close_twice.c` | Windows | the same with `CreateFile` / `WriteFile` / `CloseHandle` twice |

## Predict before you run

Two yes/no answers on paper. Every `write` returned its byte count — **can the
`close` still fail?** And if it did — **is the descriptor still open, already
closed, or unknowable?**

## Captured — 2026-09-20

**Linux**, `python:3.12-slim` container, `strace -e trace=openat,write,close`
(`make container-trace`):

```text
openat(AT_FDCWD, "closed.txt", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0644) = 3
write(3, "one\ntwo\nthree\n", 14)       = 14
close(3)                                = 0
close(3)                                = -1 EBADF (Bad file descriptor)
first  close(3): ok
second close(3): 9 Bad file descriptor
```

**Windows 11 VM** (build 26200), untraced (`make win-run`):

```text
first  CloseHandle: ok
second CloseHandle: failed, error 6 (ERROR_INVALID_HANDLE is 6)
first  close(3): ok
second close(3): 9 Bad file descriptor
```

**Windows, under NtTrace64** — which is a debugger (`make win-trace`,
`NtTrace64-CLOSE.txt`):

```text
NtWriteFile(FileHandle=0xd8, Event=0, ApcRoutine=null, ApcContext=null, IoStatusBlock=0x3b8319fb30 [0/0xe], Buffer=0x7ff745606338, Length=0xe, ByteOff
NtClose(Handle=0xd8) => 0
Exception raised by attempted close of an invalid handle
Ignoring unhandled exception from close of an invalid handle
NtClose(Handle=0xd8) => 0x0000003b8319f430 [317 'The system cannot find message text for message number 0x%1 in the message file for %2.']
RTL: RtlNtStatusToDosError(0x8319f430): No Valid Win32 Error Mapping
RTL: Edit ntos\rtl\generr.c to correct the problem
RTL: ERROR_MR_MID_NOT_FOUND is being returned
first  CloseHandle: ok
second CloseHandle: failed, error 317 (ERROR_INVALID_HANDLE is 6)
```

## What it shows

- **The descriptor is released by the first close, error or not.** The second
  `close(3)` hits nothing of ours: `EBADF`. The manual says why a retry is
  therefore never a repair: Linux "always releases the file descriptor early in
  the close operation, freeing it for reuse; the steps that may return an error
  … occur only later", so "retrying the close() after a failure return … may
  cause a reused file descriptor from another thread to be closed" (close(2)).
- **Windows says the same in two voices.** Untraced, the second `CloseHandle`
  fails with `ERROR_INVALID_HANDLE` (6). Under a debugger, Microsoft's
  documentation says the call "will throw an exception if it receives … a
  handle value that is not valid … This can happen if you close a handle
  twice" — and it does: NtTrace logged *"Exception raised by attempted close of
  an invalid handle"* and, after swallowing it, the program saw error 317
  instead of 6, because the exception path had disturbed the thread's last
  error. A double close is a bug the operating system will shout about if you
  let it.
- **Python's second `os.close` did not even reach the kernel on Windows** — the
  C runtime validates the descriptor and returns `EBADF` itself (the Python
  trace has no second `NtClose` for it). Same answer, one layer up.

## Why it matters

When a call's failure leaves you unable to tell what state you are in, report
it and stop; do not call again. The carried slide's three storage engines
reached exactly this conclusion one level down, for `fsync`, in 2018.

## Run

```sh
make run              # natively (Linux, macOS, Windows with python3)
make trace            # Linux: the four strace lines
make container-trace  # the same, on any machine with Docker
make win-build && make win-run && make win-trace    # the Windows twin over SSH (see ../win.sh)
```

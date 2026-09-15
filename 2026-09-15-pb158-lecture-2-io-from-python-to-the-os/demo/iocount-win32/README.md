---
created: 2026-09-15
tags:
  - talk
  - demo
  - operating-systems
  - windows
  - python
---

# `iocount_win32.py` — the kernel's write count, through PyWin32

Windows only, and deliberately a separate file: it needs a third-party package,
so it is the readable route rather than the default one. `../iodemo-python/`
reads the same counter through `ctypes` from the standard library.

## What it shows

There is no `strace -c` on Windows, and NtTrace lists calls without counting
them. The kernel counts anyway: `GetProcessIoCounters` fills an `IO_COUNTERS`
structure whose `WriteOperationCount` is "the number of write operations
performed" (winnt.h). PyWin32 exposes the call as
`win32process.GetProcessIoCounters(hProcess)` and returns the six fields as a
dict; `win32api.GetCurrentProcess()` is a valid handle for the current
process, so no `OpenProcess` is needed.

The script reads the counter, makes the same three writes as the other demos,
reads it again, and prints the difference. **Expect one or two, not three**:
Python buffers the three writes into one operation, and closing the file may
add another. Three `f.write` calls in the source, one or two operations in
the kernel — that gap is the whole of Part II.

## Run

```bat
pip install pywin32
python iocount_win32.py [path]
```

No container: there is no Linux equivalent of this file, and the Linux count
lives in `/proc/self/io` (`syscw`), which `../iodemo-python/iodemo.py --count`
reads.

## Sources

- [win32process.GetProcessIoCounters — PyWin32](https://mhammond.github.io/pywin32/win32process__GetProcessIoCounters_meth.html)
- [GetProcessIoCounters (winbase.h) — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters)
- [IO_COUNTERS (winnt.h) — Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters)

## Status

Not yet run on a Windows machine. The dictionary keys are verified against
PyWin32's source (`PyWinObject_FromIO_COUNTERS`); the run is not.

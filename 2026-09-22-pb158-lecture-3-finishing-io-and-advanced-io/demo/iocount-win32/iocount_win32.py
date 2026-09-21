"""Count the write operations Windows performed for this process — PyWin32 edition.

Windows only. The kernel keeps per-process I/O counters for every process;
GetProcessIoCounters reads them. PyWin32 exposes that call as
win32process.GetProcessIoCounters(hProcess), which returns a dict with the
six IO_COUNTERS fields (ReadOperationCount, WriteOperationCount,
OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount).

This is the Windows answer to `strace -c` for the question the benchmark asks:
NtTrace has no counting summary, but the kernel counted anyway, for free.

    pip install pywin32
    python iocount_win32.py [path]

Prints the counter before and after the same three writes iodemo.py makes, and
the difference. Expect a small number, not three: the writes are buffered
into one operation, and closing the file may add another.

References
    win32process.GetProcessIoCounters — mhammond.github.io/pywin32
    IO_COUNTERS (winnt.h) — learn.microsoft.com, "WriteOperationCount: the
    number of write operations performed"
"""

import sys

import win32api
import win32process


def write_operations():
    """WriteOperationCount for the current process, as the kernel counted it."""
    handle = win32api.GetCurrentProcess()  # pseudo handle, no OpenProcess needed
    return win32process.GetProcessIoCounters(handle)["WriteOperationCount"]


path = sys.argv[1] if len(sys.argv) > 1 else "iodemo.out"

before = write_operations()
with open(path, "wb") as f:
    f.write(b"one\n")
    f.write(b"two\n")
    f.write(b"three\n")
after = write_operations()

# Three write() calls in the source, and this many write operations in the
# kernel. The gap between the two numbers is the lecture.
print(f"write operations before: {before}")
print(f"write operations after:  {after}")
print(f"the three writes cost:   {after - before} operation(s)")

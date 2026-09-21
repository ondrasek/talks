"""iodemo.py — the same program as iodemo.c, one level up.

Run and trace it exactly like the C version. It prints nothing, for the same
reason: a silent program makes a legible trace.
"""

import sys

# `--count` makes the program report how many write operations the operating
# system performed on its behalf — read from the kernel's own per-process
# counters, not from a tracer. Off by default so a traced run stays exactly
# four steps; the report is itself a write to the console, and it would
# appear in the trace as one more line.
args = [a for a in sys.argv[1:] if a != "--count"]
report = "--count" in sys.argv[1:]
path = args[0] if args else "iodemo.out"


def write_operations():
    """The number of write operations the kernel has counted for this process.

    Linux: /proc/self/io, field `syscw` — "number of write syscalls"
           (proc_pid_io(5)).
    Windows: GetProcessIoCounters -> IO_COUNTERS.WriteOperationCount —
           "the number of write operations performed" (winnt.h).
    Both are kept by the kernel, cost nothing to read, and need no tracer.
    """
    if sys.platform.startswith("linux"):
        with open("/proc/self/io") as io_stats:
            for line in io_stats:
                if line.startswith("syscw:"):
                    return int(line.split()[1])
        return None
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        counters = IO_COUNTERS()
        if not k32.GetProcessIoCounters(wintypes.HANDLE(-1), ctypes.byref(counters)):
            return None
        return counters.WriteOperationCount
    return None

# 1. One deliberate failure, to make the error path visible in the trace.
try:
    open("no-such-file.txt", "rb").close()
except OSError:
    pass

# 2, 3, 4. Open, three writes, close. The close flushes.
with open(path, "wb") as f:
    f.write(b"one\n")
    f.write(b"two\n")
    f.write(b"three\n")

if report:
    n = write_operations()
    # The kernel counted every write the program made, including the ones the
    # interpreter made while starting up. Compare two runs, not one.
    print("write operations counted by the kernel:",
          "unavailable on this platform" if n is None else n)

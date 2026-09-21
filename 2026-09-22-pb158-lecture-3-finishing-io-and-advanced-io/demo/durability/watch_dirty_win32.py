#!/usr/bin/env python3
"""watch_dirty_win32.py — run save.py, then watch the Cache Manager finish the job.

    python watch_dirty_win32.py [RECORDS=100] [RECORD_BYTES=40960] [TIMEOUT_S=90]      (Windows, PyWin32)

WHAT THIS SHOWS
  The Windows twin of watch_dirty.py. save.py prints "done" and exits; its bytes
  sit in the system file cache until the Cache Manager's LAZY WRITER decides to
  write them. There is no /proc/meminfo, but the Cache Manager publishes its
  own numbers as performance counters, read here through PDH (win32pdh):

      \\Cache\\Dirty Pages              file pages modified in the system cache and not yet
                                       written to the device (1 page = 4 KiB)
      \\Cache\\Lazy Write Flushes/sec   how often the lazy writer flushed

  The program samples both every half second, runs save.py, and keeps sampling
  after it has EXITED until Dirty Pages returns to baseline.

WHAT TO LOOK AT
  1. Dirty Pages jumps by about the file size in pages the instant save.py
     exits (4 MiB = about 1,000 pages), then falls back — that fall is the
     KERNEL's done.
  2. How long after "done" it falls. On the VM we measured: 0.5-1.0 s for
     4 MiB (Linux: 5 s), and 14 s for 40 MiB, trickling about 512 pages per pass
     (Linux: 0.5 s). The two kernels answer the same question in opposite
     orders — which is the point of running both.
  3. Lazy Write Flushes/sec becomes non-zero exactly when the pages leave.

WHY IT MATTERS
  Same lesson as Linux, other clock: the program's done and the kernel's done
  are different events, and the program set neither.

Requires: pip install pywin32. Same save.py as the Linux side.
"""

import subprocess, sys, time
import win32pdh

records = sys.argv[1] if len(sys.argv) > 1 else "100"
record_bytes = sys.argv[2] if len(sys.argv) > 2 else "40960"
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0

query = win32pdh.OpenQuery()                     # a PDH query: the same counters perfmon shows
h_dirty = win32pdh.AddCounter(query, r"\Cache\Dirty Pages")
h_flush = win32pdh.AddCounter(query, r"\Cache\Lazy Write Flushes/sec")

def sample():
    win32pdh.CollectQueryData(query)
    _, dirty = win32pdh.GetFormattedCounterValue(h_dirty, win32pdh.PDH_FMT_LONG)
    try:
        _, flushes = win32pdh.GetFormattedCounterValue(h_flush, win32pdh.PDH_FMT_DOUBLE)
    except win32pdh.error:      # a rate needs two samples; the first has none
        flushes = 0.0
    return dirty, flushes

sample(); time.sleep(0.5)                        # rate counters need two samples
base_d, _ = sample()                             # baseline BEFORE the program runs
print(f"t=  0.0s  Dirty Pages={base_d:8d}   baseline   (1 page = 4 KiB)")
t0 = time.perf_counter()
out = subprocess.run([sys.executable, "save.py", "default", records, record_bytes, "saved.bin"],
                     capture_output=True, text=True, check=True).stdout.strip()
t_exit = time.perf_counter() - t0               # the PROGRAM's done: it printed and exited
d, f = sample()
print(f"t={t_exit:5.1f}s  Dirty Pages={d:8d}   <- save.py has EXITED: \"{out}\"")
settled = None; last = None
while True:
    time.sleep(0.5)
    t = time.perf_counter() - t0
    d, f = sample()
    if (d, round(f, 1)) != last:
        print(f"t={t:5.1f}s  Dirty Pages={d:8d}   Lazy Write Flushes/sec={f:5.1f}")
        last = (d, round(f, 1))
    if d <= base_d + 16:                        # back to baseline: the CACHE MANAGER's done
        settled = t; break
    if t > timeout:
        break
print()
if settled is None:
    print(f"not back to baseline after {timeout:.0f}s — something else is dirtying pages; rerun on a quiet machine")
else:
    print(f"Cache Manager finished writing {settled - t_exit:.1f}s AFTER the program said done ({settled:.1f}s after start).")

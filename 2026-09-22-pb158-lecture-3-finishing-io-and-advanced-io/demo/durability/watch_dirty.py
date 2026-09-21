#!/usr/bin/env python3
"""watch_dirty.py — run save.py, then watch the kernel finish the job.

    python3 watch_dirty.py [RECORDS=100] [RECORD_BYTES=40960] [TIMEOUT_S=90]

WHAT THIS SHOWS
  save.py prints "done" and exits. Its bytes are not on the disk: they sit in
  the kernel's page cache — memory that belongs to no process — until a kernel
  timer or threshold decides otherwise. The kernel publishes how much such
  data it holds: the Dirty and Writeback lines in /proc/meminfo. This program
  samples them every half second, runs save.py, and keeps sampling after the
  program has EXITED until the count falls back to where it started. The gap
  between the program's "done" and that moment is the number the room predicts.

WHAT TO LOOK AT
  1. Dirty jumps by about the file size the instant save.py exits (1 kB per KiB
     written, the file is now the kernel's problem), then stays there.
  2. Seconds later it drops back to baseline: THAT is when the bytes reached
     the device. On the machines we measured: about five seconds for a 6 KiB or
     a 4 MiB file, half a second for 40 MiB.
  3. The two sysctls printed first. The one a student reads first,
     dirty_expire_centisecs (30 s), did NOT apply; the flusher's wake interval,
     dirty_writeback_centisecs (5 s), matched. The kernel has several rules for
     when; which one fired is an inference from the timing, so say so.

WHY IT MATTERS
  Pull the power inside that window and "done" was false. Neither the program
  nor Python chose the five seconds; the kernel did. Whose done did you measure?
"""

import subprocess, sys, time

records = sys.argv[1] if len(sys.argv) > 1 else "100"
record_bytes = sys.argv[2] if len(sys.argv) > 2 else "40960"
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0

def meminfo():                    # the kernel's own count of file data it has not written yet (kB)
    vals = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            if k in ("Dirty", "Writeback"):
                vals[k] = int(v.split()[0])
    return vals["Dirty"], vals["Writeback"]

def sysctl(name):
    try:
        with open(f"/proc/sys/vm/{name}") as f:
            return f.read().strip()
    except OSError:
        return "?"

print(f"vm.dirty_expire_centisecs    = {sysctl('dirty_expire_centisecs')}   (a dirty page older than this is written back)")
print(f"vm.dirty_writeback_centisecs = {sysctl('dirty_writeback_centisecs')}   (the flusher thread wakes this often)")
print()
base_d, base_w = meminfo()        # baseline BEFORE the program runs: other things dirty pages too
print(f"t=  0.0s  Dirty={base_d:8d} kB  Writeback={base_w:6d} kB   baseline")
t0 = time.perf_counter()
out = subprocess.run([sys.executable, "save.py", "default", records, record_bytes, "saved.bin"],
                     capture_output=True, text=True, check=True).stdout.strip()
t_exit = time.perf_counter() - t0  # the PROGRAM's done: it printed and exited
d, w = meminfo()
print(f"t={t_exit:5.1f}s  Dirty={d:8d} kB  Writeback={w:6d} kB   <- save.py has EXITED: \"{out}\"")
settled = None
last = None
while True:
    time.sleep(0.5)
    t = time.perf_counter() - t0
    d, w = meminfo()
    state = (d, w)
    if state != last:
        print(f"t={t:5.1f}s  Dirty={d:8d} kB  Writeback={w:6d} kB")
        last = state
    if d <= base_d + 64 and w == 0:  # back to baseline: the KERNEL's done
        settled = t
        break
    if t > timeout:
        break
print()
if settled is None:
    print(f"not back to baseline after {timeout:.0f}s — something else is dirtying pages; rerun on a quiet machine")
else:
    print(f"kernel finished writing {settled - t_exit:.1f}s AFTER the program said done "
          f"({settled:.1f}s after start).")

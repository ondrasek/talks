---
created: 2026-09-20
tags:
  - talk
  - demo
  - operating-systems
  - io
  - durability
---

# Whose *done* was it? — a program says done, the kernel writes later

Section 3 of Lecture 3: *so when is it safe?* `save.py` writes a hundred
records to a file and prints **done**. `watch_dirty.py` runs it and then keeps
reading the kernel's own count of file data it has not yet written to the
device — `Dirty` and `Writeback` in `/proc/meminfo` — every half second,
until the count falls back to where it started. The gap between the program's
*done* and the kernel's is the number the room predicts.

| file | what |
|---|---|
| `save.py MODE` | writes 100 records one of four ways: `default` (runtime buffer, emptied at close), `flush` (`f.flush()` per record), `fsync` (`flush` + `os.fsync()` per record), `unbuffered` |
| `watch_dirty.py` | runs `save.py default`, samples `Dirty`/`Writeback` until baseline; prints `vm.dirty_expire_centisecs` and `vm.dirty_writeback_centisecs` first |

## Predict before you run

The program has printed *done* and exited. **How long until the kernel actually
writes your bytes to the device?** Pick one, on paper: *under a second · about
five seconds · about thirty seconds · not until shutdown.* Then
`make container-watch`.

## Captured in the container, 2026-09-20

`python:3.12-slim` on Docker's Linux VM: kernel `6.8.0-139-generic` (Ubuntu
24.04, aarch64), root filesystem ext4 `commit=30,data=ordered`, `laptop_mode`
0, `dirty_background_ratio` 10, `dirty_ratio` 20. The container's writable
layer is overlayfs over that ext4; one run was repeated on a bind-mounted
plain ext4 directory and gave the same result.

```text
vm.dirty_expire_centisecs    = 3000   (a dirty page older than this is written back)
vm.dirty_writeback_centisecs = 500    (the flusher thread wakes this often)

t=  0.0s  Dirty=    1176 kB  Writeback=    72 kB   baseline
t=  0.0s  Dirty=    5132 kB  Writeback=    72 kB   <- save.py has EXITED: "done: 100 records x 40960 B, mode=default, 1.8 ms"
t=  0.5s  Dirty=    5284 kB  Writeback=     0 kB
t=  1.5s  Dirty=    5288 kB  Writeback=     0 kB
t=  2.0s  Dirty=    5292 kB  Writeback=     0 kB
t=  2.5s  Dirty=    5364 kB  Writeback=     0 kB
t=  3.0s  Dirty=    5380 kB  Writeback=     0 kB
t=  4.0s  Dirty=    5388 kB  Writeback=     0 kB
t=  5.0s  Dirty=     676 kB  Writeback=     0 kB

kernel finished writing 5.0s AFTER the program said done (5.0s after start).
```

Five runs, three sizes:

| written | runs | kernel's *done* after the program's |
|---|---|---|
| 100 × 40 KiB = 4 MiB | 3 (two on overlayfs, one on plain ext4) | **5.0 s, 5.5 s, 5.5 s** |
| 100 × 64 B = 6 KiB | 1 | **5.5 s** |
| 1000 × 40 KiB = 40 MiB | 1 | **0.5 s** |

**What the numbers say.** The program said *done* about five seconds before
the kernel did, for a file of any ordinary size. The bytes spent those five
seconds in the page cache — level 3 of Lecture 2's stack — in the machine's
memory, owned by nobody's process. Pull the power in that window and *done*
was false. Neither the program nor the language runtime chose the five
seconds; the kernel did.

**What they also say, and this is the honest part.** The sysctl a student
reads first, `dirty_expire_centisecs`, says a dirty page is written back once
it is thirty seconds old. Nothing here waited thirty seconds. The pages went
out at the flusher thread's first wake-up (`dirty_writeback_centisecs`, five
seconds), and forty mebibytes went out in under a second, before any timer.
The kernel has several rules for *when*, and the one that applied is not the
one the manual page leads with — *which* rule fired is an inference from the
timing, not something this demo can show. The lesson survives either way:
the kernel's *done* is on the kernel's clock, and you did not set it.

## The supporting count — what the last handoff costs

`make container-count`: `strace -c -f -e trace=write,fsync,fdatasync`, 100
records × 64 bytes, the four modes.

```text
== default
done: 100 records x 64 B, mode=default, 0.2 ms
100.00    0.000031           5         6           write
== flush
done: 100 records x 64 B, mode=flush, 1.1 ms
100.00    0.000126           1       101           write
== fsync
done: 100 records x 64 B, mode=fsync, 67.3 ms
 71.70    0.002212          22       100           fsync
 28.30    0.000873           8       101           write
== unbuffered
done: 100 records x 64 B, mode=unbuffered, 1.0 ms
100.00    0.000156           1       101           write
```

| mode | `write` calls | `fsync` calls | wall time |
|---|---|---|---|
| default | 6 (one for the data, the rest are the runtime's own) | 0 | 0.2 ms |
| flush per record | 101 | 0 | 1.1 ms |
| **fsync per record** | 101 | **100** | **67.3 ms** |
| unbuffered | 101 | 0 | 1.0 ms |

Asking the kernel to push each record to the device cost **sixty times** the
wall time of merely handing it to the kernel, for the same hundred `write`
calls. That is the price of the last software handoff, it is why programs
that are not databases never pay it, and it is why the sentence the room
heard in Lecture 2 stands: the only real answer to durability, and still best
effort, is a well-tested UPS. (Note the `strace -c` column: 2.2 ms *inside*
`fsync` against 67 ms wall — the rest is the process waiting for the device;
"count under the tracer, time without it".)

Not shown here, and deliberately: whether the device then wrote the bytes to
the medium. No tool in this folder can see that (Lecture 2, slide 32), and
the PostgreSQL fsync-gate case in
[[Zettelkasten/A failed fsync() is not retryable]] is the evidence that even
the kernel's *done* can be wrong.

## Windows — the same two observations, other names

Ondra, 2026-09-20: the Windows half gets demos, not a slide of documentation.

| file | Linux twin | what |
|---|---|---|
| `watch_dirty_win32.py` (PyWin32) | `watch_dirty.py` | runs `save.py default`, then samples the Cache Manager's own counters through PDH — `\Cache\Dirty Pages` and `\Cache\Lazy Write Flushes/sec` — every half second until the dirty count returns to baseline |
| `iocost.c` (Win32) | `save.py`'s four modes under `strace -c` | 100 × 4096-byte records four ways: `WriteFile` into the cache · `FlushFileBuffers` per record (the `fsync` twin) · `FILE_FLAG_WRITE_THROUGH` · `FILE_FLAG_NO_BUFFERING`; wall time from `QueryPerformanceCounter`, and the kernel's own `WriteOperationCount` from `GetProcessIoCounters` — Lecture 2's counter |
| `Makefile.msvc` | `Makefile` | `nmake /f Makefile.msvc run` / `trace` / `watch` |

**The prediction, Windows form.** Same question — the program has printed
*done*; how long until the Cache Manager writes the bytes? — but the cadence
is the lazy writer's, not a sysctl's: Windows Internals, as the durability note
records, has it wake every second and queue an eighth of the pages not
recently flushed. So the options are the same four and the room should expect
a *different* answer from Linux's five seconds. The concept note's own open
question — whether Windows has any user-visible dirty-page-age knob like
`dirty_expire_centisecs` — stays open; this demo does not settle it.

### Captured — 2026-09-20, Ondra's Windows 11 VM (build 26200, ARM64), over SSH

**`iocost.exe`** (x64, MSVC 19.51), untraced:

```text
done: 100 records x 4096 B, mode=default,      0.7 ms, kernel write operations: 100
done: 100 records x 4096 B, mode=flush,       27.9 ms, kernel write operations: 100
done: 100 records x 4096 B, mode=writethrough, 25.2 ms, kernel write operations: 100
done: 100 records x 4096 B, mode=nobuffer,     9.9 ms, kernel write operations: 100
```

| mode | kernel write ops | wall | Linux twin |
|---|---|---|---|
| `WriteFile` into the cache | 100 | 0.7 ms | `flush` per record, 1.1 ms |
| `FlushFileBuffers` per record | 100 | **27.9 ms** | `fsync` per record, 67.3 ms |
| `FILE_FLAG_WRITE_THROUGH` | 100 | 25.2 ms | — |
| `FILE_FLAG_NO_BUFFERING` | 100 | 9.9 ms | — |

**Forty times**, for asking the device to confirm each record. Linux's figure
was sixty, and the two ratios must not be divided into each other: `iocost.c`
writes 4096-byte records and `save.py`'s counted run writes 64-byte records, a
64-fold difference in payload per record that neither run controls for. What is
the same on both platforms is the shape — one to two orders of magnitude of wall
time for the confirmation, at an unchanged call count — on a virtual disk. Write-through costs the same as an
explicit flush per record, which is what it is. The kernel counted 100 write
operations in every mode: the count says how many times the program asked,
the wall time says who waited.

**Traced** with NtTrace64 (`-filter NtCreateFile,NtWriteFile,NtFlushBuffersFile`;
full captures `NtTrace64-IOCOST-flush.txt`, `NtTrace64-IOCOST-default.txt`):

```text
== flush:   101 NtWriteFile   100 NtFlushBuffersFile   5 NtCreateFile     (done: 84.3 ms under the tracer)
== default: 101 NtWriteFile     0 NtFlushBuffersFile   5 NtCreateFile     (done: 26.6 ms under the tracer)
NtWriteFile(FileHandle=0xec, ..., IoStatusBlock [0/0x1000], Length=0x1000, ...) => 0
NtFlushBuffersFile(FileHandle=0xec, IoStatusBlock [0/0]) => 0
```

One `NtWriteFile` per record in both, one `NtFlushBuffersFile` after each in
flush mode, the 101st write being the `done:` line to the console. Under the
tracer the untraced 0.7 ms became 26.6 ms — "count under the tracer, time
without it", on Windows too.

**`watch_dirty_win32.py`** (PyWin32 under the Program Files Python 3.14), four runs:

```text
run 1, 4 MiB   t=  0.0s  Dirty Pages=     194   baseline
               t=  0.1s  Dirty Pages=    1201   <- save.py has EXITED
               t=  0.6s  Dirty Pages=     176   Lazy Write Flushes/sec= 27.9
               Cache Manager finished writing 0.5s AFTER the program said done
run 2, 4 MiB   ... 115 -> 1122 -> (0.6s: 1122) -> 1.1s: 127     finished 1.0s after done
run 3, 4 MiB   ... 154 -> 1156 -> 0.6s: 109                     finished 0.5s after done
run 4, 40 MiB  t=  0.1s  Dirty Pages=   10117   <- save.py has EXITED
               t=  0.6s  Dirty Pages=    9606   Lazy Write Flushes/sec=  6.0
               t=  2.1s  Dirty Pages=    9092   Lazy Write Flushes/sec=  5.9
               t=  3.1s  Dirty Pages=    8582   ...   (about 512 pages per pass, roughly every 1.5 s)
               t= 13.7s  Dirty Pages=    5018
               t= 14.2s  Dirty Pages=       9   Lazy Write Flushes/sec=271.6
               Cache Manager finished writing 14.1s AFTER the program said done
```

| written | Windows: Cache Manager's *done* after the program's | Linux (same demo): kernel's *done* |
|---|---|---|
| 4 MiB (×3) | **0.5 s, 1.0 s, 0.5 s** | 5.0 s, 5.5 s, 5.5 s |
| 40 MiB | **14.1 s** | 0.5 s |

**What the numbers say.** The two kernels answer the same question in
opposite orders. For a small file Windows' lazy writer had the pages out
within a second; Linux waited for its flusher's five-second wake. For a large
file Linux wrote everything at once because a threshold tripped, while the
Windows lazy writer trickled about 512 pages per pass, roughly every second
and a half, for fourteen seconds, then flushed the remainder in one burst.
Both are the kernel's own clock, neither is the program's, and the four
options on the prediction slide fit both: *under a second* on Windows,
*about five* on Linux, and for the big file each platform lands where the
other did not. Which Cache Manager rule produced the 512-page passes is an
inference from the timeline — Windows Internals' description of the lazy
writer is the source to read, not this trace.

## Run

```sh
make run              # the four modes, natively, timings only
make watch            # the prediction, Linux: watch_dirty.py reads /proc/meminfo
make count            # the four-mode syscall counts (Linux only)
make container-watch  # the watch above, on any machine with Docker
make container-count  # the counts above, on any machine with Docker

make win-build        # the Windows half, from macOS over SSH (../win.sh): iocost.exe
make win-run          # iocost.exe, the four modes, timed and counted by the kernel (GetProcessIoCounters)
make win-count        # the same — on Windows the program carries its own count
make win-watch        # the prediction, Windows: watch_dirty_win32.py (PyWin32) — save.py, then the Cache Manager's dirty pages until they drain
make win-trace        # iocost.exe under NtTrace64, captures fetched back
```

On the Windows machine itself, from an x64 Developer Command Prompt in this
folder: `nmake /f Makefile.msvc run`, `nmake /f Makefile.msvc watch`,
`nmake /f Makefile.msvc trace`. The watch writes a 4 MiB file (100 × 40960
bytes) and samples for up to 90 s; a busy machine makes the baseline noisy,
so run it on a quiet one.

The `Dirty` figure is the kernel's, so it includes whatever else the machine
is writing. Run it on a quiet machine; if it never returns to baseline, the
watcher says so rather than reporting a number.

---
created: 2026-09-20
tags:
  - talk
  - demo
  - operating-systems
  - io
---

# One call, many buffers — and bytes the process never touches

Part 9 of Lecture 3: *scatter/gather and zero-copy*. Two small programs, both
traced in the Linux container.

| file | what |
|---|---|
| `gather.py separate` / `gather` | a message that is three buffers in the program — header, body, trailer — written as three `write` calls, or as one `writev` |
| `zerocopy.py copy` / `sendfile` | a 4 MiB file moved into a pipe (a child drains it): a read-into-the-process-then-write loop, or `sendfile`, where the kernel moves the bytes and the process never holds them |

## Predict before you run

Three buffers, one message. **How many system calls does it take — three, one,
or zero — and how many times are the bytes copied?** Write it down, then
`make container-trace`.

## Captured in the container, 2026-09-20

`python:3.12-slim`, `strace -e trace=write,writev`. (`PYTHONDONTWRITEBYTECODE=1`
so CPython does not open the trace with three `.pyc` writes of its own.)

```text
== three write() calls
write(3, "HEADER  ", 8)                 = 8
write(3, "body body body body body body bo"..., 40) = 40
write(3, " TRAILER\n", 9)               = 9

== one writev() call
writev(3, [{iov_base="HEADER  ", iov_len=8}, {iov_base="body body body body body body bo"..., iov_len=40}, {iov_base=" TRAILER\n", iov_len=9}], 3) = 57
```

**Three crossings became one.** The kernel *gathered* the three buffers; the
return value is the whole message, 57 bytes. Nothing was copied in the program
to make that happen — the three buffers stayed where they were and the kernel
read them in order. POSIX adds the promise that matters for a log file: the
`writev` is atomic with respect to other writers on the same descriptor, so
another process cannot land its line between your header and your body. Three
`write` calls give no such promise. `readv` is the mirror image on the read
side: one crossing *scatters* into several buffers.

## Zero-copy — `make container-count`

`strace -c -e trace=read,write,sendfile`, 4 MiB, the parent process only:

```text
== copy: read into the process, write out
done: mode=copy, 4 MiB, 128 data syscall(s) in this process, 2.6 ms
 77.58    0.001900          27        69           write
 22.42    0.000549           6        83           read
100.00    0.002449          16       152           total

== sendfile: the kernel moves the bytes
done: mode=sendfile, 4 MiB, 64 data syscall(s) in this process, 2.0 ms
 72.71    0.001018         509         2           write
 26.21    0.000367           5        64           sendfile
  1.07    0.000015           0        18           read
100.00    0.001400          16        84           total
```

| mode | data syscalls | copies through user space | wall |
|---|---|---|---|
| copy loop, 64 KiB chunks | 64 `read` + 64 `write` = **128** | **two per chunk** — into the buffer, out of it | 2.6 ms |
| `sendfile` | **64** `sendfile` | **none** — the process never holds a byte of the file | 2.0 ms |

(The other `read`/`write` calls in both tables are the interpreter starting up
and the `done:` line; the copy loop's 64 + 64 and the 64 `sendfile` calls are
the transfer.)

**What the numbers say.** Half the system calls, and no copy through the
process: `sendfile` hands the kernel a source descriptor, a destination
descriptor and a length, and the bytes go from the page cache to the pipe
without visiting user space. Each call moved 64 KiB because that is what the
pipe would take at once — a pipe's capacity, not `sendfile`'s limit.

**What they do not say.** At 4 MiB into a pipe on one machine, the wall-time
difference is small and would not survive a second run's noise; the honest
claim is the copies avoided and the calls halved, not a speed-up figure.
Zero-copy moves bytes the kernel already has; it cannot help a program that
must look at the bytes, and it does nothing for durability — the same four
levels sit below the pipe as below a file.

## Windows

The same two ideas under other names, on the slide from
[[Concepts/Operating Systems/Scatter-Gather and Zero-Copy I-O]]: `WSASend`
with an array of `WSABUF` (gather), `ReadFileScatter` / `WriteFileGather`, and
`TransmitFile` (a file to a socket without user-space copies). No Windows
capture in this folder.

## Run

```sh
make run              # the four programs, natively (Linux; macOS has writev but not this sendfile)
make trace            # the writev prediction (Linux only)
make count            # the copy vs sendfile counts (Linux only)
make container-trace  # the trace above, on any machine with Docker
make container-count  # the counts above, on any machine with Docker
```

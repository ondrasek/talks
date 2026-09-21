#!/usr/bin/env python3
"""close_twice.py — close a descriptor, then close it again. What does the second close hit?

    python3 close_twice.py            (Linux, macOS, Windows)

WHAT THIS SHOWS
  The carried Lecture 2 slide says: never retry a failed close(). This program
  shows the mechanical reason. It opens a file, closes it, and closes the SAME
  descriptor number again — which is exactly what a retry does. The second
  close fails with EBADF (bad file descriptor): the number was released by the
  first close, whether or not that first close reported an error. On Linux the
  manual page is explicit: the kernel "always releases the file descriptor
  early in the close operation, freeing it for reuse", so a retry can only ever
  hit nothing — or, in a program with other threads, SOMEBODY ELSE's newly
  opened file that was handed the same number.

WHAT TO LOOK AT
  Under strace (make trace): close(3) = 0, then close(3) = -1 EBADF. Two
  crossings, one descriptor, one of them already gone.

WHY IT MATTERS
  When a call's failure leaves you unable to tell what state you are in, the
  only safe move is to report it and stop retrying. Three storage engines
  reached the same conclusion for fsync in 2018 (Part 5 / Part 6).
"""
import os, sys

fd = os.open("closed.txt", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
os.write(fd, b"one\ntwo\nthree\n")
os.close(fd)                       # the descriptor number is released HERE, error or not
print(f"first  close({fd}): ok")
try:
    os.close(fd)                   # "the retry": the number no longer refers to anything of ours
    print(f"second close({fd}): ok (unexpected)")
except OSError as e:
    print(f"second close({fd}): {e.errno} {e.strerror}")   # EBADF on Linux and Windows alike

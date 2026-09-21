#!/usr/bin/env python3
"""nttrace-count.py — count an NtTrace capture the way `strace -c` counts.

    python3 nttrace-count.py CAPTURE.txt [CAPTURE2.txt ...]

NtTrace lists every native call it saw and counts nothing. This reads its
output and prints one row per native call: how many times, and how many of
those returned an error status (the `[…]` annotation NtTrace appends). The
lecture compares Linux and Windows by counts, so both sides need a table.
Deterministic: a line is a call if it starts with an `Nt` name and an open
parenthesis. Nothing is interpreted.
"""
import re, sys
from collections import Counter

CALL = re.compile(r"^\s*(Nt\w+)\(")
ERROR = re.compile(r"=>\s*0x[89A-Fa-f][0-9A-Fa-f]{7}\b")   # NTSTATUS with the severity bit set

for path in sys.argv[1:] or ["-"]:
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8", errors="replace").read()
    calls, errors = Counter(), Counter()
    for line in text.splitlines():
        m = CALL.match(line)
        if not m:
            continue
        calls[m.group(1)] += 1
        if ERROR.search(line):
            errors[m.group(1)] += 1
    total = sum(calls.values())
    print(f"== {path}: {total} native call(s)")
    print(f"{'calls':>8} {'errors':>7}  syscall")
    for name, n in calls.most_common():
        print(f"{n:>8} {errors[name] or '':>7}  {name}")

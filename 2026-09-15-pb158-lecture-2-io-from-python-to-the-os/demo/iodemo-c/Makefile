# GNU make — Linux (and macOS). MSVC ships nmake, not GNU make; use
# Makefile.msvc there.

CC     ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -O0 -g
IMAGE  ?= pb158-iodemo-c

iodemo: iodemo.c
	$(CC) $(CFLAGS) -o $@ $<

# The Linux half of the matched pair.
.PHONY: trace
trace: iodemo
	strace -e trace=openat,write,close ./iodemo iodemo.out

# The kernel's own count of this process's write operations (/proc/self/io).
.PHONY: count
count: iodemo
	./iodemo iodemo.out --count

# ── the Linux container: Debian + gcc + strace + ltrace, program built inside ─
.PHONY: image
image:
	docker build -t $(IMAGE) .

# strace and ltrace are ptrace clients; Docker drops CAP_SYS_PTRACE by default.
.PHONY: container-trace
container-trace: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE)

.PHONY: container-count
container-count: image
	docker run --rm $(IMAGE) ./iodemo iodemo.out --count

.PHONY: clean
clean:
	rm -f iodemo iodemo.out

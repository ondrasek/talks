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

# Lecture 3, section 5 — the same fourteen bytes over a TCP socket, netcat on
# the other side. iodemo cannot open a socket by path (a socket cannot be
# reopened through /dev/stdout), so iodemo writes to a pipe into the client
# netcat, and BOTH netcats are traced: the client's call that puts the bytes
# on the socket, the listener's call that takes them off. Linux only.
PORT ?= 9000
.PHONY: socket-trace
socket-trace: iodemo
	@rm -f received.txt
	@strace -e trace=socket,bind,listen,accept4,read,close -o server.strace \
	  nc -l 127.0.0.1 $(PORT) > received.txt & \
	sleep 0.5; \
	./iodemo /dev/stdout | strace -e trace=socket,connect,write,sendto,read,close -o client.strace nc -N 127.0.0.1 $(PORT); \
	wait
	@echo "== client nc (writer) — strace"; cat client.strace
	@echo "== listener nc (reader) — strace"; cat server.strace
	@echo "== received.txt"; cat received.txt

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

.PHONY: container-socket
container-socket: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE) make socket-trace

.PHONY: clean
clean:
	rm -f iodemo iodemo.out received.txt server.strace client.strace

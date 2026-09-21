# GNU make. Two ways to wait for input that never comes, counted.
PYTHON ?= python3
IMAGE  ?= pb158-waiting
PIPES  ?= 100
SECS   ?= 2

.PHONY: run
run:
	$(PYTHON) wait_blocking.py $(PIPES) $(SECS)
	$(PYTHON) wait_epoll.py $(PIPES) $(SECS)

# The counts the lecture is about: system calls per program while nothing happens.
.PHONY: count
count:
	strace -c -f $(PYTHON) wait_blocking.py $(PIPES) $(SECS) 2>&1 | grep -E "calls|read|epoll|total"
	strace -c -f $(PYTHON) wait_epoll.py $(PIPES) $(SECS) 2>&1 | grep -E "calls|read|epoll|total"

.PHONY: image
image:
	docker build -t $(IMAGE) .

.PHONY: container-count
container-count: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE)

# ── the Windows twins, from macOS over SSH (see ../win.sh) ───────────────────
.PHONY: win-build win-run win-trace win-trace-py win-fetch
win-build:    ; ../win.sh build waiting
win-run:      ; ../win.sh run waiting
win-trace:    ; ../win.sh trace waiting
win-trace-py: ; ../win.sh trace-py waiting
win-fetch:    ; ../win.sh fetch waiting

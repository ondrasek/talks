# GNU make. One descriptor, closed twice. Linux (container) and macOS.
PYTHON ?= python3
IMAGE  ?= pb158-close

.PHONY: run trace image container-trace
run:
	$(PYTHON) close_twice.py

# The two close() lines the slide shows.
# The interpreter opens and closes dozens of its own files first; show only what
# follows our openat of closed.txt.
trace:
	strace -e trace=openat,write,close $(PYTHON) close_twice.py 2>&1 | grep -A4 "closed.txt" | grep -E "closed.txt|^close|^write\(3|first|second"

image:
	docker build -t $(IMAGE) .

container-trace: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE)

# ── the Windows twin, from macOS over SSH (see ../win.sh) ───────────────────
.PHONY: win-build win-run win-trace win-fetch
win-build: ; ../win.sh build close
win-run:   ; ../win.sh run close
win-trace: ; ../win.sh trace close
win-fetch: ; ../win.sh fetch close

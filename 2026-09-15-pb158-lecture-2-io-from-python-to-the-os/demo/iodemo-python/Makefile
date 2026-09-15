# GNU make — the same targets as ../iodemo-c/Makefile, for the Python twin.
# Nothing to compile; the targets exist so both folders are driven the same way.

PYTHON ?= python3
IMAGE  ?= pb158-iodemo-python

.PHONY: run
run:
	$(PYTHON) iodemo.py iodemo.out

.PHONY: count
count:
	$(PYTHON) iodemo.py iodemo.out --count

# The Linux half of the matched pair, one level up: the same three names, and
# the interpreter's own start-up traffic in front of them.
.PHONY: trace
trace:
	strace -e trace=openat,write,close $(PYTHON) iodemo.py iodemo.out

# ── the Linux container ──────────────────────────────────────────────────────
.PHONY: image
image:
	docker build -t $(IMAGE) .

.PHONY: container-trace
container-trace: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE)

.PHONY: container-count
container-count: image
	docker run --rm $(IMAGE) $(PYTHON) iodemo.py iodemo.out --count

.PHONY: clean
clean:
	rm -f iodemo.out

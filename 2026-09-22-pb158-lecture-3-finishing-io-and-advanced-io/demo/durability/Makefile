# GNU make. Whose "done" was it? The program's, the kernel's, or the device's.
PYTHON       ?= python3
IMAGE        ?= pb158-durability
RECORDS      ?= 100
RECORD_BYTES ?= 64         # small records: the four-mode syscall counts stay legible
WATCH_BYTES  ?= 40960      # 100 x 40 KiB = 4 MiB, big enough to see in /proc/meminfo Dirty (kB)
TIMEOUT      ?= 90

.PHONY: run
run:
	$(PYTHON) save.py default    $(RECORDS) $(RECORD_BYTES)
	$(PYTHON) save.py flush      $(RECORDS) $(RECORD_BYTES)
	$(PYTHON) save.py fsync      $(RECORDS) $(RECORD_BYTES)
	$(PYTHON) save.py unbuffered $(RECORDS) $(RECORD_BYTES)

# The prediction: how long after "done" does the kernel write the bytes? (Linux only)
.PHONY: watch
watch:
	$(PYTHON) watch_dirty.py $(RECORDS) $(WATCH_BYTES) $(TIMEOUT)

# The supporting count: write and fsync calls, and time spent in them, per mode (Linux only)
.PHONY: count
count:
	@for m in default flush fsync unbuffered; do \
	  echo "== $$m"; \
	  strace -c -f -e trace=write,fsync,fdatasync $(PYTHON) save.py $$m $(RECORDS) $(RECORD_BYTES) 2>&1 | grep -E "done:|calls|write|fsync|total"; \
	done

.PHONY: image
image:
	docker build -t $(IMAGE) .

.PHONY: container-watch
container-watch: image
	docker run --rm $(IMAGE) make watch

.PHONY: container-count
container-count: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE) make count

# ── the Windows twins, from macOS over SSH (see ../win.sh) ───────────────────
.PHONY: win-build win-run win-trace win-trace-py win-fetch
win-build:    ; ../win.sh build durability
win-run:      ; ../win.sh run durability
win-watch:    ; ../win.sh watch
win-trace:    ; ../win.sh trace durability
win-trace-py: ; ../win.sh trace-py durability
win-fetch:    ; ../win.sh fetch durability

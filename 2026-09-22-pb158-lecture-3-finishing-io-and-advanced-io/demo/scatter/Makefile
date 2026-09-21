# GNU make. One call, many buffers; and bytes the process never touches. Linux only.
# PYTHONDONTWRITEBYTECODE: without it CPython writes three .pyc files at start-up
# and the trace opens with three write() calls that are not ours.
PYTHON ?= env PYTHONDONTWRITEBYTECODE=1 python3
IMAGE  ?= pb158-scatter
MIB    ?= 4

.PHONY: run
run:
	$(PYTHON) gather.py separate
	$(PYTHON) gather.py gather
	$(PYTHON) zerocopy.py copy $(MIB)
	$(PYTHON) zerocopy.py sendfile $(MIB)

# The prediction: how many system calls carry three buffers?
.PHONY: trace
trace:
	@echo "== three write() calls"; strace -e trace=write,writev $(PYTHON) gather.py separate 2>&1 | grep -E "^write|^writev|done:"
	@echo "== one writev() call";   strace -e trace=write,writev $(PYTHON) gather.py gather   2>&1 | grep -E "^write|^writev|done:"

# The supporting count: copies through user space, or none.
.PHONY: count
count:
	@echo "== copy: read into the process, write out"; strace -c -e trace=read,write,sendfile $(PYTHON) zerocopy.py copy $(MIB) 2>&1 | grep -E "done:|calls|read|write|sendfile|total"
	@echo "== sendfile: the kernel moves the bytes";  strace -c -e trace=read,write,sendfile $(PYTHON) zerocopy.py sendfile $(MIB) 2>&1 | grep -E "done:|calls|read|write|sendfile|total"

.PHONY: image
image:
	docker build -t $(IMAGE) .

.PHONY: container-trace
container-trace: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE) make trace

.PHONY: container-count
container-count: image
	docker run --rm --cap-add SYS_PTRACE $(IMAGE) make count

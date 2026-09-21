# A Linux box for the durability demo: CPython, strace, and a kernel whose
# /proc/meminfo and vm.dirty_* sysctls the room can read. Dirty pages are
# counted by the kernel the container runs on, so the numbers describe that
# kernel — Docker's Linux VM on a macOS host, the real one on a Linux host.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strace make && rm -rf /var/lib/apt/lists/*
WORKDIR /demo
COPY save.py watch_dirty.py Makefile ./
CMD ["make", "watch"]

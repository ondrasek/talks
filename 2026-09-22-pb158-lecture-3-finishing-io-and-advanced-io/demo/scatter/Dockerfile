# A Linux box for the scatter/gather and zero-copy demo: CPython and strace.
# writev(2) and sendfile(2) are Linux system calls; macOS has writev but its
# sendfile has a different shape, so the numbers come from here.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strace make && rm -rf /var/lib/apt/lists/*
WORKDIR /demo
COPY gather.py zerocopy.py Makefile ./
CMD ["make", "trace"]

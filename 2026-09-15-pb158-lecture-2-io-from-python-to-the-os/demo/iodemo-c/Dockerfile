# A Linux box for iodemo.c: compiler, make, and the two tracers the lecture
# uses. Debian's packages, nothing built from source, so the image is what a
# lab machine would have after `apt install`. The release matches the Python
# twin's python:3.12-slim base; bookworm has no ltrace package on arm64.
#
# Build and run from this directory:
#
#   docker build -t pb158-iodemo-c .
#   docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c            # the trace
#   docker run --rm pb158-iodemo-c ./iodemo iodemo.out --count     # the count
#   docker run --rm --cap-add SYS_PTRACE pb158-iodemo-c ltrace ./iodemo iodemo.out
#
# --cap-add SYS_PTRACE, belt and braces: Docker drops CAP_SYS_PTRACE, and the
# ptrace system call itself is blocked by the default seccomp profile on
# kernels before 4.8 (docs.docker.com/engine/security/seccomp). strace and
# ltrace are ptrace clients. The --count run needs nothing extra:
# /proc/self/io is the kernel's own accounting, readable without a tracer.
FROM debian:trixie-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make strace ltrace \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /demo
COPY iodemo.c Makefile ./
RUN make iodemo

# The Linux half of the matched pair. Same three names as the NtTrace side.
CMD ["strace", "-e", "trace=openat,write,close", "./iodemo", "iodemo.out"]

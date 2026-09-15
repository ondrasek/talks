# A Linux box for iodemo.py: CPython plus the two tracers the lecture uses.
#
# Build and run from this directory:
#
#   docker build -t pb158-iodemo-python .
#   docker run --rm --cap-add SYS_PTRACE pb158-iodemo-python              # the trace
#   docker run --rm pb158-iodemo-python python3 iodemo.py iodemo.out --count
#   docker run --rm --cap-add SYS_PTRACE pb158-iodemo-python strace -c python3 iodemo.py iodemo.out
#
# --cap-add SYS_PTRACE, belt and braces: Docker drops CAP_SYS_PTRACE, and the
# ptrace system call itself is blocked by the default seccomp profile on
# kernels before 4.8 (docs.docker.com/engine/security/seccomp). strace and
# ltrace are ptrace clients. The --count run needs nothing extra.
#
# Expect noise. CPython opens dozens of files before it reaches iodemo.py —
# every import, every path probe — so the openat filter shows the interpreter
# starting up before the four lines that matter. That noise is the argument
# for tracing the C program on the slide, and this container is where the room
# can see it for themselves.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends strace ltrace \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /demo
COPY iodemo.py ./

CMD ["strace", "-e", "trace=openat,write,close", "python3", "iodemo.py", "iodemo.out"]

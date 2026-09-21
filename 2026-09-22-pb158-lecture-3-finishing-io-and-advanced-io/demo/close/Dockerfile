# A Linux box for close_twice.py: CPython and strace.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strace make && rm -rf /var/lib/apt/lists/*
WORKDIR /demo
COPY close_twice.py Makefile ./
CMD ["make", "trace", "PYTHON=env PYTHONDONTWRITEBYTECODE=1 python3"]

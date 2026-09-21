# A Linux box for the waiting demo: CPython and strace. On Linux `selectors`
# picks epoll, which is the mechanism the lecture names; on the lecturer's
# macOS it would pick kqueue, so the counts must come from here.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strace make && rm -rf /var/lib/apt/lists/*
WORKDIR /demo
COPY wait_blocking.py wait_epoll.py Makefile ./
CMD ["make", "count"]

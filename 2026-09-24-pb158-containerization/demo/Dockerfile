FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends strace \
    && rm -rf /var/lib/apt/lists/*
COPY app.py /app/app.py
CMD ["python", "/app/app.py"]

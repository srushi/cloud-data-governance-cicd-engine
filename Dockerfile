# Validation engine image: slim Python, engine + fixtures baked in.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY engine ./engine
COPY scripts ./scripts
COPY fixtures ./fixtures
COPY main.py ./

RUN mkdir -p /app/out
VOLUME ["/app/out"]

EXPOSE 8080

# Default: run the offline audit against the bundled fixtures.
ENTRYPOINT ["python", "main.py"]
CMD ["run-audit", "--source", "local", "--report", "out"]

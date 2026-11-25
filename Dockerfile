# The app in one container: FastAPI + the static page + the sample data.
#   docker build -t weroad-chat .
#   docker run -p 8000:8000 --env-file .env -e ANTHROPIC_API_KEY weroad-chat
# Credentials are passed at run time, never baked into the image (.dockerignore keeps .env out). With an
# `ant auth login` profile instead of a key: -e ANTHROPIC_AUTH_TOKEN=<ant auth print-credentials --access-token>.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes, not on every code edit.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY samples ./samples

# Bytecode compiled now: the app runs as a user that can't write __pycache__ under /app. logs/ is the only
# writable folder (logs/turns.jsonl).
RUN python -m compileall -q app \
    && useradd --create-home --uid 10001 app \
    && mkdir logs && chown app logs
USER app

EXPOSE 8000

# Healthy once the startup warm-up is done (/api/ready), so an orchestrator sends traffic only when the
# first reply will be fast. No curl in the slim image: Python does the request.
HEALTHCHECK --interval=10s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import json, sys, urllib.request; sys.exit(0 if json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=3))['assistant_ready'] else 1)"]

# One process: sessions live in its memory (app/sessions.py), so several workers wouldn't share them.
# Not run.py: that is for development (opens a browser, reloads on every save).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

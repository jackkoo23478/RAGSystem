FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/huggingface

WORKDIR /app

# The default PyTorch wheel on Linux brings several GB of CUDA libraries. The container has no GPU, so take the CPU build.
# This layer comes first: it is large and rarely changes, so Docker reuses it from its cache.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Download the embedding model now, so the first question does not have to fetch it
# and the container also works without internet access.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

# Run as a normal user, not root. /data holds the database and /app/data/uploads the uploaded files;
# both are mounted as volumes, so they must belong to that user.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /app/data/uploads \
    && chown -R app:app /data /app/data
USER app

EXPOSE 8000

# Bring the database up to date, then start the server. "exec" lets the server receive the stop signal.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM python:3.11-slim

# deps nativas para OCR
RUN apt-get update && apt-get install -y \
    poppler-utils tesseract-ocr ghostscript libgl1 file curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8088 QUAR_DIR=/srv/quarantine
VOLUME ["/srv/quarantine"]

# health
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://localhost:8088/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8088", "--workers", "1"]

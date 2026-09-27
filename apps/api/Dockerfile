# Not yet built/tested locally (no Docker in the original dev environment
# — see docs/architecture.md). Kept current for when Docker is available.
FROM python:3.12-slim

WORKDIR /app

# Tesseract reads scanned documents; LibreOffice converts legacy .doc
# (Word is not available on Linux). .docx/.rtf/.odt need neither.
RUN apt-get update     && apt-get install -y --no-install-recommends tesseract-ocr libreoffice-writer-nogui     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

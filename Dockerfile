FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-core.txt .
RUN pip install --no-cache-dir -r requirements-core.txt

# Install Playwright browsers (Heavy step)
RUN playwright install --with-deps chromium

# Pre-download Models (Heavy step)
COPY download_models.py .
RUN python download_models.py

# Install Light Dependencies (Frequent changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]

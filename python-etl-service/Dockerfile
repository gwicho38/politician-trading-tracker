# Python ETL Service for Politician Trading Tracker
# Uses pdfplumber for PDF parsing and Playwright for anti-bot protected sites

FROM python:3.11-slim

# Install system dependencies for pdfplumber and Playwright
RUN apt-get update && apt-get install -y \
    libpoppler-cpp-dev \
    poppler-utils \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium only for size)
RUN playwright install chromium

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8080

# Run the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

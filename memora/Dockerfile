# Base image with Python 3.11
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install required system packages (ffmpeg for audio processing, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies first for caching
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=user . .

# Ensure SQLite data directory is writable
RUN mkdir -p $HOME/app/data

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Start FastAPI application via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]


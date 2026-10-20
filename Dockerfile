FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output for cleaner container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies including ffmpeg for video encoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code into container
COPY . /app/

# Default entrypoint for running commands or interactive shell
CMD ["bash"]

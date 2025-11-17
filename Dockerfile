# SOLUTION 1: Use Python 3.10 with Debian Bullseye (recommended)
FROM python:3.10-slim-bullseye
WORKDIR /app

# Install system dependencies including ffmpeg and ffprobe
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Verify ffmpeg installation
RUN ffmpeg -version && ffprobe -version

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p downloads temp_thumbs

CMD gunicorn app:app & python3 bot.py

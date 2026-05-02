# Use official Python 3.13 slim image as base
# slim variant removes unnecessary system packages — smaller image size
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first — Docker caches this layer
# If requirements.txt hasn't changed, pip install is skipped on rebuild
COPY requirements.txt .

# Install build dependencies needed for scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for mounted volumes
RUN mkdir -p data logs

# Expose port 8000
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
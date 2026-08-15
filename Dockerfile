# Use official Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

# Set working directory
WORKDIR /app

# Install system dependencies (for numpy, scikit-learn, matplotlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Create data directory (mounted as volume)
RUN mkdir -p /app/data

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["python", "-m", "ground_station.web.app"]

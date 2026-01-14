# Use standard Python image (lighter than full GUI base)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for docker client or nicegui deps)
# docker-cli is needed to communicate with host docker socket
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose NiceGUI port
EXPOSE 8080

# Run the dashboard
CMD ["python", "dashboard.py"]

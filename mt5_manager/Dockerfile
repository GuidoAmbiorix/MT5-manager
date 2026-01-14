FROM jlesage/baseimage-gui:alpine

# Name of the application
ENV APP_NAME="MT5 Manager"

# Install required system packages
# python3-tkinter: for GUI
# py3-pip: for python dependencies
# docker-cli: so we can mount docker.sock and use docker client
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-tkinter \
    docker-cli

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
# customtkinter and docker
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate the start script
# The base image expects the application to run in foreground
# We write a small shell script to start our python app
RUN echo '#!/bin/sh' > /startapp.sh && \
    echo 'exec python3 /app/main.py' >> /startapp.sh && \
    chmod +x /startapp.sh

# The base image handles VNC/NoVNC automatically
# It exposes port 5800 for web access

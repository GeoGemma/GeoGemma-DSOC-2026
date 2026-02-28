# Use Alpine-based image
FROM python:3.10-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies needed for Python packages
# This includes GIS libraries, visualization tools, and cryptography
RUN apk add --no-cache \
    # Build tools
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    make \
    # GDAL dependencies
    gdal-dev \
    geos-dev \
    proj-dev \
    # Visualization dependencies
    freetype-dev \
    libpng-dev \
    openblas-dev \
    # Cryptography dependencies
    openssl-dev \
    libffi-dev \
    # JSON dependencies
    libjpeg-turbo-dev \
    zlib-dev \
    # For matplotlib
    jpeg-dev \
    tiff-dev \
    # Required for numpy/scipy
    lapack-dev

# Create necessary directories
RUN mkdir -p /app/data/cache /app/data/temp /app/logs /app/config

# Create empty config files
RUN touch /app/config/api_keys.yaml
RUN touch /app/config/server_config.yaml
RUN touch /app/earth-engine.json

# Copy requirements file
COPY requirements.txt .

# Install Python packages with a timeout for each package
# Use a script to install packages one by one with error handling
RUN echo "#!/bin/sh" > /install_packages.sh && \
    echo "set -e" >> /install_packages.sh && \
    echo "cat requirements.txt | while read package; do" >> /install_packages.sh && \
    echo "  if [ -n \"\$package\" ] && ! [[ \$package == \\#* ]]; then" >> /install_packages.sh && \
    echo "    echo \"Installing \$package...\"" >> /install_packages.sh && \
    echo "    pip install --no-cache-dir \$package || echo \"Failed to install \$package, continuing...\"" >> /install_packages.sh && \
    echo "  fi" >> /install_packages.sh && \
    echo "done" >> /install_packages.sh && \
    chmod +x /install_packages.sh && \
    /install_packages.sh

# Ensure core packages are installed
RUN pip install --no-cache-dir fastapi uvicorn pydantic requests google-generativeai

# Copy the rest of the application code
COPY . .

# Port on which the server will run
EXPOSE 8090

# Run the application
CMD ["python", "-m", "src.main", "--host", "0.0.0.0"]
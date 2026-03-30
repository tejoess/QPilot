# Use slim python image for efficiency
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy everything else, but put it inside the 'backend' folder
COPY . ./backend/

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn. 
# We use 0.0.0.0 to allow access from outside the container
CMD ["uvicorn", "backend.main:backend", "--host", "0.0.0.0", "--port", "8000"]

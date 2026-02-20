FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (setuptools first for pkg_resources on Python 3.13)
COPY requirements.txt .
RUN pip install --no-cache-dir "setuptools>=65.0.0,<70" && \
    pip install --no-cache-dir -r requirements.txt

# Copy .env file from backend folder (if exists)
COPY .env* ./

# Copy project files
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles

# Expose port
EXPOSE 8000

# Run migrations and start server with Daphne (ASGI for WebSocket support)
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    daphne -b 0.0.0.0 -p 8000 config.asgi:application


FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy .env file from backend folder (if exists)
COPY .env* ./

# Copy project files
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3


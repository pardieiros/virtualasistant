#!/bin/bash

set -e

echo "=== Docker Setup Script for Personal Assistant ==="
echo ""

# Ask for domain
read -p "Enter your domain (e.g., example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "Error: Domain is required"
    exit 1
fi

echo ""
echo "Domain set to: $DOMAIN"
echo ""

# Update nginx configuration with domain
echo "Updating nginx configuration..."
# macOS compatible sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/server_name _;/server_name $DOMAIN;/g" nginx/nginx.conf
else
    sed -i.bak "s/server_name _;/server_name $DOMAIN;/g" nginx/nginx.conf
fi

# Update backend .env if it exists
if [ -f "backend/.env" ]; then
    echo "Updating backend/.env..."
    # Update ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS with domain
    if grep -q "ALLOWED_HOSTS" backend/.env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1/g" backend/.env
        else
            sed -i.bak "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1/g" backend/.env
        fi
    else
        echo "ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1" >> backend/.env
    fi
    
    if grep -q "CORS_ALLOWED_ORIGINS" backend/.env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://$DOMAIN:1443,http://$DOMAIN:1080,http://localhost:5173|g" backend/.env
        else
            sed -i.bak "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://$DOMAIN:1443,http://$DOMAIN:1080,http://localhost:5173|g" backend/.env
        fi
    else
        echo "CORS_ALLOWED_ORIGINS=https://$DOMAIN:1443,http://$DOMAIN:1080,http://localhost:5173" >> backend/.env
    fi
else
    echo "Warning: backend/.env not found. Creating template..."
    echo ""
    echo "Please provide your PostgreSQL database connection details:"
    read -p "DB_HOST (PostgreSQL server address): " DB_HOST
    read -p "DB_PORT [5432]: " DB_PORT
    DB_PORT=${DB_PORT:-5432}
    read -p "DB_NAME: " DB_NAME
    read -p "DB_USER: " DB_USER
    read -s -p "DB_PASSWORD: " DB_PASSWORD
    echo ""
    
    cat > backend/.env << EOF
SECRET_KEY=django-insecure-change-me-in-production-$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
CORS_ALLOWED_ORIGINS=https://$DOMAIN:1443,http://$DOMAIN:1080,http://localhost:5173
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=marco-assistente
SOCKET_APP_ID=
SOCKET_APP_KEY=
SOCKET_APP_SECRET=
SOCKET_HOST=soketi
SOCKET_PORT=6001
SOCKET_USE_TLS=False
EOF
    echo "Database configuration saved to backend/.env"
fi

# Update frontend .env if it exists
if [ -f "frontend/.env" ]; then
    echo "Updating frontend/.env..."
    if grep -q "VITE_API_BASE_URL" frontend/.env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=/api|g" frontend/.env
        else
            sed -i.bak "s|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=/api|g" frontend/.env
        fi
    else
        echo "VITE_API_BASE_URL=/api" >> frontend/.env
    fi
else
    echo "Warning: frontend/.env not found. Creating template..."
    cat > frontend/.env << EOF
VITE_API_BASE_URL=/api
VITE_SOCKET_HOST=$DOMAIN
VITE_SOCKET_PORT=6001
VITE_SOCKET_KEY=
VITE_SOCKET_USE_TLS=false
EOF
fi

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Generate self-signed certificate if it doesn't exist
if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
    echo ""
    echo "Generating self-signed SSL certificate for HTTPS..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=PT/ST=Lisbon/L=Lisbon/O=Personal Assistant/CN=$DOMAIN"
    echo "SSL certificate generated!"
fi

# Clean up backup files (only on Linux)
if [[ "$OSTYPE" != "darwin"* ]]; then
    find . -name "*.bak" -type f -delete
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Configuration updated with domain: $DOMAIN"
echo ""
echo "Next steps:"
echo "1. Review and update backend/.env and frontend/.env if needed"
echo "2. Run 'docker-compose up -d' to start all services"
echo ""
echo "Services will be available at:"
echo "  - HTTP:  http://$DOMAIN:1080"
echo "  - HTTPS: https://$DOMAIN:1443"
echo ""


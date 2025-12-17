# Docker Setup Guide

This guide explains how to set up and run the Personal Assistant application using Docker.

## Prerequisites

- Docker and Docker Compose installed
- Domain name (or you can use localhost for testing)

## Quick Start

1. **Run the setup script:**
   ```bash
   ./setup-docker.sh
   ```
   
   The script will:
   - Ask for your domain name
   - Update nginx configuration with your domain
   - Update or create `.env` files for backend and frontend
   - Generate self-signed SSL certificates for HTTPS (if they don't exist)

2. **Review environment files:**
   - Check `backend/.env` and `frontend/.env`
   - Update any settings as needed (database passwords, API keys, etc.)

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - HTTP: `http://your-domain:1080`
   - HTTPS: `https://your-domain:1443`

## Services

The docker-compose setup includes:

- **backend**: Django REST API (connects to external PostgreSQL server)
- **frontend**: React/Vite application (served via nginx)
- **nginx**: Reverse proxy that:
  - Serves the frontend on ports 1080 (HTTP) and 1443 (HTTPS)
  - Proxies `/api` requests to the backend

**Note:** This setup assumes you have an external PostgreSQL database server. Configure the database connection in `backend/.env`.

## Environment Files

### Backend `.env`

The backend `.env` file should contain:

```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
DB_HOST=your-postgres-server-address
DB_PORT=5432
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
CORS_ALLOWED_ORIGINS=https://your-domain.com:1443,http://your-domain.com:1080
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=marco-assistente
SOCKET_APP_ID=
SOCKET_APP_KEY=
SOCKET_APP_SECRET=
SOCKET_HOST=soketi
SOCKET_PORT=6001
SOCKET_USE_TLS=False
```

**Important:** Replace `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` with your external PostgreSQL server details.

### Frontend `.env`

The frontend `.env` file should contain:

```env
VITE_API_BASE_URL=/api
VITE_SOCKET_HOST=your-domain.com
VITE_SOCKET_PORT=6001
VITE_SOCKET_KEY=
VITE_SOCKET_USE_TLS=false
```

## SSL Certificates

The setup script generates self-signed SSL certificates. For production, you should replace these with valid certificates:

1. Place your certificate at `nginx/ssl/cert.pem`
2. Place your private key at `nginx/ssl/key.pem`

## Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild services
docker-compose up -d --build

# Access backend container
docker-compose exec backend bash

# Run migrations manually
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

## Troubleshooting

### Database connection errors

Ensure the `DB_HOST` in `backend/.env` points to your external PostgreSQL server. Make sure:
- The database server is accessible from the Docker network
- Firewall rules allow connections from the Docker host
- Database credentials are correct
- The database exists and the user has proper permissions

### CORS errors

Check that `CORS_ALLOWED_ORIGINS` in `backend/.env` includes your domain with both HTTP and HTTPS protocols.

### Frontend can't connect to backend

Verify that `VITE_API_BASE_URL` in `frontend/.env` is set to `/api` (relative path for nginx proxy).

### SSL certificate errors

For self-signed certificates, browsers will show a warning. You can:
- Accept the security exception in your browser
- Replace with valid certificates from a CA
- Use Let's Encrypt certificates with certbot


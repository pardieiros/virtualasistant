# Push Notifications Setup Guide

This guide explains how to set up push notifications for the Personal Assistant application.

## Overview

The application uses:
- **Celery** with **Redis** for background task processing
- **Web Push API** for browser push notifications
- **VAPID** (Voluntary Application Server Identification) for authentication

## Backend Setup

### 1. Install Dependencies

The required packages are already in `requirements.txt`:
- `celery==5.3.4`
- `redis==5.0.1`
- `pywebpush==1.14.0`
- `py-vapid==1.11.0`

Install them:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Redis

Redis is already configured in `docker-compose.yml`. If running locally:

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis
# Linux: sudo apt-get install redis-server
```

### 3. Generate VAPID Keys

Generate VAPID keys for push notifications:

```bash
cd backend
python generate_vapid_keys.py
```

This will output:
```
VAPID_PUBLIC_KEY=your-public-key-here
VAPID_PRIVATE_KEY=your-private-key-here
VAPID_EMAIL=mailto:your-email@example.com
```

### 4. Update Backend .env File

Add these variables to `backend/.env`:

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# VAPID Keys for Web Push Notifications
VAPID_PUBLIC_KEY=your-public-key-from-step-3
VAPID_PRIVATE_KEY=your-private-key-from-step-3
VAPID_EMAIL=mailto:your-email@example.com
```

### 5. Run Database Migrations

Create the PushSubscription model:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 6. Start Celery Worker and Beat

In separate terminals:

```bash
# Terminal 1: Celery Worker
cd backend
celery -A config worker --loglevel=info

# Terminal 2: Celery Beat (scheduler)
cd backend
celery -A config beat --loglevel=info
```

Or using Docker, add to your docker-compose.yml:

```yaml
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config worker --loglevel=info
    env_file:
      - ./backend/.env
    depends_on:
      - redis
      - backend
    networks:
      - app-network

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config beat --loglevel=info
    env_file:
      - ./backend/.env
    depends_on:
      - redis
      - backend
    networks:
      - app-network
```

## Frontend Setup

The frontend is already configured with:
- Service worker for push notifications (`public/sw.js`)
- Push notification utilities (`src/utils/pushNotifications.ts`)
- Integration in Agenda page

### How It Works

1. When a user visits the Agenda page, the app automatically requests push notification permission
2. If granted, the subscription is registered with the backend
3. Celery Beat runs a task every minute to check for upcoming events (within 15 minutes)
4. When an event is found, push notifications are sent to all user's registered subscriptions

## Testing

### Test Push Notifications

1. Start the backend, Redis, Celery worker, and Celery beat
2. Open the application in a browser that supports push notifications (Chrome, Firefox, Edge)
3. Navigate to the Agenda page
4. Grant push notification permission when prompted
5. Create an event that starts in the next 15 minutes
6. Wait up to 1 minute for the notification to arrive

### Manual Test

You can also test manually by creating a Django management command or using the Django shell:

```python
from assistant.models import PushSubscription, AgendaEvent
from assistant.services.push_notification_service import send_push_notification

# Get a subscription
subscription = PushSubscription.objects.first()

# Send a test notification
send_push_notification(
    subscription=subscription,
    title="Test Notification",
    body="This is a test push notification",
    data={'type': 'test'}
)
```

## API Endpoints

### Push Subscriptions

- `GET /api/push-subscriptions/` - List user's subscriptions
- `POST /api/push-subscriptions/register/` - Register a new subscription
  ```json
  {
    "endpoint": "https://...",
    "keys": {
      "p256dh": "...",
      "auth": "..."
    }
  }
  ```
- `POST /api/push-subscriptions/unregister/` - Unregister a subscription
  ```json
  {
    "endpoint": "https://..."
  }
  ```
- `GET /api/push-subscriptions/vapid-public-key/` - Get VAPID public key

## Troubleshooting

### Notifications Not Appearing

1. Check browser console for errors
2. Verify VAPID keys are correctly set in `.env`
3. Ensure Celery worker and beat are running
4. Check Redis is running and accessible
5. Verify the service worker is registered (check Application tab in browser DevTools)

### Service Worker Issues

1. Clear browser cache and service workers
2. Rebuild the frontend: `npm run build`
3. Check browser console for service worker errors

### Celery Not Running Tasks

1. Check Celery worker logs for errors
2. Verify Redis connection: `redis-cli ping` should return `PONG`
3. Check Celery beat is running and scheduling tasks

## Production Considerations

1. Use a proper email address in `VAPID_EMAIL`
2. Ensure Redis is properly secured
3. Use environment-specific VAPID keys (don't share between dev/prod)
4. Monitor Celery task execution
5. Set up proper logging and error handling
6. Consider rate limiting for push notifications


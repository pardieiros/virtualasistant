# Quick Setup Guide

## Backend Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database and Ollama settings
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Frontend Quick Start

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your API and Soketi settings
npm run dev
```

## First Time Setup Checklist

- [ ] PostgreSQL database created
- [ ] Backend `.env` configured
- [ ] Frontend `.env` configured
- [ ] Ollama installed and running
- [ ] Ollama model created (or use existing model)
- [ ] Soketi installed and running (optional)
- [ ] Database migrations run
- [ ] Superuser created
- [ ] Test login works

## Testing the Chat

1. Login with your superuser credentials
2. Go to Chat page
3. Try: "Adiciona leite à lista de compras"
4. Check Shopping List page to see the item
5. Try voice input (microphone button)

## Common Issues

**Ollama connection error:**
- Make sure Ollama is running: `ollama serve`
- Check `OLLAMA_BASE_URL` in backend `.env`
- Verify model name in `OLLAMA_MODEL`

**WebSocket not working:**
- Check Soketi is running
- Verify Soketi credentials in both backend and frontend `.env`
- Check browser console for connection errors

**JWT token issues:**
- Make sure you're logged in
- Check browser localStorage for `access_token`
- Token expires after 7 days (refresh token: 30 days)


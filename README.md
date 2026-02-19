# Personal Assistant - AI-Powered Assistant Web App

A modern, full-stack personal assistant application built with Django, React, and Ollama. Features a beautiful dark elegant UI with voice interaction, real-time updates, and integration capabilities for shopping lists, agenda management, notes, and Home Assistant.

## 🎨 Design Theme

**Dark Elegant (Black + Gold + Warm Gray)**
- Primary Gold: `#EAB308`
- Soft Gold: `#FACC15`
- Charcoal: `#111113`
- Warm Gray: `#27272A`
- Premium, cinematic aesthetic perfect for a Jarvis-like assistant

## 🏗️ Tech Stack

### Backend
- **Django 5** with Django REST Framework
- **PostgreSQL** database
- **JWT Authentication** (djangorestframework-simplejwt)
- **Ollama** LLM integration (local)
- **Soketi** (Pusher-compatible) for real-time WebSocket updates
- **Python 3** with type hints

### Frontend
- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **PWA** ready (manifest, service worker)
- **Web Speech API** for voice input/output
- **Pusher-js** for WebSocket client

## 📋 Features

1. **Conversational AI Assistant**
   - Text and voice interaction
   - Tool/action execution (shopping, agenda, notes, Home Assistant)
   - Natural Portuguese (Portugal) responses

2. **Shopping List Management**
   - Detailed items with quantities, stores, categories
   - Priority levels and status tracking
   - Grouped by preferred store

3. **Agenda/Calendar**
   - Event management with dates, times, locations
   - Category organization
   - All-day event support

4. **Personal Notes**
   - Simple note-taking
   - Edit and delete functionality

5. **Home Assistant Integration** (Placeholder)
   - Configuration UI
   - Service call structure ready for future integration

6. **Real-time Updates**
   - WebSocket integration via Soketi
   - Live updates across connected clients

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 12+
- Ollama installed and running locally
- Soketi server (optional, for real-time features)

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server:**
   ```bash
   python manage.py runserver
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

### Ollama Setup

1. **Install Ollama:**
   Visit [https://ollama.ai](https://ollama.ai) and install Ollama

2. **Create or use a model:**
   ```bash
   # Example: pull qwen3-vl:8b
   ollama pull qwen3-vl:8b
   ```
   
   Or use an existing model like `llama2`, `mistral`, etc.

3. **Update `.env` in backend:**
   ```env
   OLLAMA_MODEL=qwen3-vl:8b
   OLLAMA_BASE_URL=http://localhost:11434
   ```

4. **Start Ollama:**
   ```bash
   ollama serve
   ```

### Soketi Setup (Optional, for Real-time Features)

1. **Install Soketi:**
   ```bash
   npm install -g @soketi/soketi
   ```

2. **Start Soketi:**
   ```bash
   soketi start
   ```
   
   Default configuration:
   - Host: `localhost`
   - Port: `6001`
   - App ID, Key, Secret: Generated automatically (check Soketi output)

3. **Update backend `.env`:**
   ```env
   SOCKET_APP_ID=your-app-id
   SOCKET_APP_KEY=your-app-key
   SOCKET_APP_SECRET=your-app-secret
   SOCKET_HOST=localhost
   SOCKET_PORT=6001
   SOCKET_USE_TLS=False
   ```

4. **Update frontend `.env`:**
   ```env
   VITE_SOCKET_HOST=localhost
   VITE_SOCKET_PORT=6001
   VITE_SOCKET_KEY=your-app-key
   VITE_SOCKET_USE_TLS=false
   ```

## 📁 Project Structure

```
personalassistance/
├── backend/
│   ├── config/          # Django settings
│   ├── assistant/       # Main app
│   │   ├── models.py    # Database models
│   │   ├── serializers.py
│   │   ├── views.py     # API views
│   │   ├── urls.py
│   │   └── services/    # Business logic
│   │       ├── ollama_client.py
│   │       ├── tool_dispatcher.py
│   │       ├── pusher_service.py
│   │       └── homeassistant_client.py
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/         # API client
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom hooks
│   │   ├── context/     # React context
│   │   ├── types/       # TypeScript types
│   │   └── utils/       # Utilities
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/token/` - Obtain JWT token
- `POST /api/auth/token/refresh/` - Refresh token

### Chat
- `POST /api/chat/` - Send message to assistant

### Shopping Items
- `GET /api/shopping-items/` - List items (filters: status, store, search)
- `POST /api/shopping-items/` - Create item
- `PATCH /api/shopping-items/{id}/` - Update item
- `DELETE /api/shopping-items/{id}/` - Delete item

### Agenda
- `GET /api/agenda/` - List events (filters: start_date, end_date)
- `POST /api/agenda/` - Create event
- `PATCH /api/agenda/{id}/` - Update event
- `DELETE /api/agenda/{id}/` - Delete event

### Notes
- `GET /api/notes/` - List notes
- `POST /api/notes/` - Create note
- `PATCH /api/notes/{id}/` - Update note
- `DELETE /api/notes/{id}/` - Delete note

### Home Assistant
- `GET /api/homeassistant/my_config/` - Get config
- `POST /api/homeassistant/my_config/` - Update config

## 🤖 LLM Tool System

The assistant uses an ACTION JSON format to trigger backend actions:

```json
ACTION: {"tool": "tool_name", "args": {...}}
```

Available tools:
- `add_shopping_item` - Add item to shopping list
- `show_shopping_list` - Retrieve current shopping list
- `add_agenda_event` - Add event to agenda
- `save_note` - Save a personal note
- `homeassistant_call_service` - Call Home Assistant service (future)

## 🎤 Voice Features

- **Speech-to-Text**: Browser Web Speech API (Portuguese)
- **Text-to-Speech**: Browser Speech Synthesis API
- Toggle voice on/off in chat interface

## 🔐 Security Notes

- JWT tokens stored in localStorage (consider httpOnly cookies for production)
- Home Assistant tokens stored in database (consider encryption)
- CORS configured for development origins
- Change `SECRET_KEY` in production

## 🚧 Future Enhancements

- [ ] Streaming LLM responses
- [ ] Better TTS (backend-based)
- [ ] Full Home Assistant integration
- [ ] User preferences and customization
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Advanced agenda views (calendar)
- [ ] Shopping list sharing

## 📝 License

This project is for personal use. Modify as needed.

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

---

Built with ❤️ using Django, React, and Ollama

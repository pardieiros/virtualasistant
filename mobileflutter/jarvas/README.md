# Jarvas – Flutter Client

Flutter app (Cupertino, iOS-first) for the **Virtual Assistant** Django backend. Connects to your server, logs in with JWT, and uses the Chat API.

## Requirements

- Flutter SDK (e.g. 3.10+)
- Xcode (for iOS) or Android SDK
- Virtual Assistant backend running (see repo root) with Nginx on port **1080** (HTTP) or **1443** (HTTPS)

## Setup

1. **Install dependencies**
   ```bash
   cd mobileflutter/jarvas
   flutter pub get
   ```

2. **Configure server**
   - Run the app (iOS Simulator, Android emulator, or device).
   - On first launch you see **Setup**: enter the backend URL (e.g. `http://192.168.1.90:1080` or `http://10.0.2.2:1080` for Android emulator).
   - Tap **Test connection**. If OK, tap **Continue to Login**.

3. **Login**
   - Use the same credentials as the Django backend (create a user in Django admin if needed).
   - JWT access and refresh tokens are stored securely.

## Run

- **iOS Simulator**: `flutter run`
- **Android emulator**: `flutter run -d android` (use `http://10.0.2.2:1080` as server URL for host machine)
- **Device on local network**: use your machine’s IP, e.g. `http://192.168.1.90:1080`

For HTTP on local network, ensure `NSAllowsLocalNetworking` is set in `ios/Runner/Info.plist`. For production, use HTTPS.

## Backend connection (Django Virtual Assistant)

- **Default base URL**: `https://virtualassistant.ddns.net` (configurable in Setup).
- **HTTP (REST)** – used for chat and API:
  - `POST /api/auth/token/` – login → `access`, `refresh`
  - `POST /api/chat/` – send message → `reply`, `action`
  - `POST /api/chat/stream/` – streaming chat (SSE)
  - `GET/POST /api/agenda/`, `/api/notes/`, `/api/todos/`, `/api/conversations/` – REST resources
- **WebSockets** – used for Voice and Classroom (not for text chat):
  - `wss://virtualassistant.ddns.net/ws/voice/?token=ACCESS_TOKEN` – voice conversation
  - `wss://virtualassistant.ddns.net/ws/classroom/?token=ACCESS_TOKEN` – classroom tutor  
  In the Chat screen, tap the link icon (🔗) and use **Test WebSocket** to verify the WebSocket connection.

## Features

- **Setup**: Server URL, test connection, persist URL.
- **Login**: Username/password, JWT stored in secure storage.
- **Chat**: Send messages and receive assistant replies; history sent for context.
- **UI**: Cupertino theme, message bubbles, empty state, logout from chat.

## Theme

- **Colors**: Aqua `#8FD7EA`, lavender `#BEABE1`, accent `#A7BAE4` (see `lib/core/theme.dart`).

## Project structure

- `lib/main.dart` – entry, `ProviderScope` + `JarvasApp`.
- `lib/app.dart` – `CupertinoApp`, theme, routing (Setup → Login → Chat).
- `lib/core/` – config, errors, theme.
- `lib/services/` – api_client, auth_service, chat_service, storage_service.
- `lib/state/` – Riverpod providers (storage, api client, auth).
- `lib/ui/screens/` – Setup, Login, Chat.

## Tests

```bash
flutter test
```

- `test/widget_test.dart` – app starts with `ProviderScope` and `JarvasApp`.
- `test/storage_test.dart` – storage/URL helpers.

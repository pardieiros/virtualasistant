# Jarvas – Flutter iOS Client

Flutter app (Cupertino, iOS-first) for the Gateway/Orchestrator Node.js backend. Connects to your server, logs in, and uses Chat over WebSocket with streaming and plugins (e.g. Shopping list).

## Requirements

- Flutter SDK (e.g. 3.29+)
- Xcode (for iOS)
- Backend running (see repo root) at a URL like `http://192.168.1.90:3000`

## Setup

1. **Clone and open**
   ```bash
   cd mobileflutter/jarvas
   flutter pub get
   ```

2. **Configure server**
   - Run the app (iOS Simulator or device).
   - On first launch you see **Setup**: enter the backend URL (e.g. `http://192.168.1.90:3000`).
   - Tap **Test connection**. If OK, the URL is saved and you go to **Login**.

3. **Login**
   - Use the same credentials as the backend (default `admin` / `admin` if unchanged).
   - The app sends `X-Client: jarvas-mobile` so the backend returns `accessToken` and `refreshToken` in the response (required for mobile).

## Run

- **iOS Simulator**
  ```bash
  flutter run
  ```
  Or open `ios/Runner.xcworkspace` in Xcode and run.

- **iOS device**
  - Connect the device, select it in Xcode/Flutter, then run.
  - For HTTP on local network, the app uses `NSAllowsLocalNetworking` (see `ios/Runner/Info.plist`). For production, use HTTPS and tighten ATS if needed.

- **Android** (optional)
  ```bash
  flutter run -d android
  ```

## Backend connection

- **Base URL**: Stored after Setup (e.g. `http://192.168.1.90:3000`).
- **Endpoints** (see `lib/core/config.dart`):
  - `GET /api/v1/status` – test connection
  - `POST /api/v1/auth/login` – login (body: `username`, `password`; mobile gets tokens in body)
  - `GET /api/v1/plugins` – list plugins (auth required)
  - `GET/POST/DELETE /api/v1/shopping/items` – shopping list (auth required)
  - WebSocket: `ws://SERVER/ws/chat?token=ACCESS_TOKEN`

If your Node backend uses different paths, change `ApiPaths` and `wsChatPath()` in `lib/core/config.dart` and the API calls in `lib/services/api_client.dart` and `lib/services/ws_chat_service.dart`.

## Features

- **Setup**: Server URL, test connection, persist URL.
- **Login**: Username/password, token stored in secure storage.
- **Chat**: WebSocket streaming, tokens and tool_call/tool_result shown, reconnect with backoff.
- **Plugins**: List enabled plugins from backend; open Shopping list (or “Open in chat” for others).
- **Settings**: Theme (Light/Dark/System), language (pt/en/System), server, logout, About.

## Theme and assets

- **Logo**: Uses `assets/personal_assistance_logo_nobg.png` (e.g. on Setup).
- **Colors**: Aqua `#8FD7EA`, lavender `#BEABE1`, accent `#A7BAE4` (see `lib/core/theme.dart`).
- **Launch screen**: iOS uses `LaunchScreen.storyboard` and `Assets.xcassets/LaunchImage.imageset`. To show the app logo on launch, replace the LaunchImage assets with your logo (e.g. copy `personal_assistance_logo_nobg.png` into that imageset).

## i18n

- **pt / en** via `lib/l10n/app_localizations.dart` (and optional `.arb` in `lib/l10n/`).
- Language selectable in Settings (Portuguese / English / System).

## Project structure

- `lib/main.dart` – entry, `ProviderScope` + `JarvasApp`.
- `lib/app.dart` – `CupertinoApp`, theme, locale, routing (Setup → Login → Chat).
- `lib/core/` – config, errors, logger, theme, utils.
- `lib/services/` – api_client, auth_service, plugins_service, storage_service, ws_chat_service.
- `lib/state/` – Riverpod providers and controllers (auth, settings, chat, plugins).
- `lib/ui/screens/` – Setup, Login, Chat, Plugins, Shopping list, Settings.
- `lib/ui/widgets/` – MessageBubble, StreamingBubble, Cupertino dialogs.

## Tests

```bash
flutter test
```

- `test/widget_test.dart` – app starts with `ProviderScope` and `JarvasApp`.
- `test/ws_parser_test.dart` – WebSocket message parsing (assistant_token, tool_call, etc.).
- `test/storage_test.dart` – `normalizeBaseUrl` and basic helpers.

## Screenshots

_(Add screenshots of Setup, Login, Chat, Plugins, Settings here if desired.)_

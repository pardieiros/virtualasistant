# Voice Conversation Mode - Setup Guide

## Visão Geral

Este guia explica como fazer deploy do novo modo de conversa telefónica no Jarvas, que permite conversas de voz em tempo real usando WebSockets.

## Arquitetura

```
┌─────────────┐      WebSocket (WSS)      ┌─────────────┐
│   Browser   │ ←─────────────────────→   │    Nginx    │
│  Frontend   │                            │   (Proxy)   │
└─────────────┘                            └─────────────┘
       ↑                                          ↓
       │                                    WebSocket
       │                                          ↓
       │                              ┌───────────────────┐
       │                              │  Django Channels  │
       │                              │   (ASGI Server)   │
       │                              └───────────────────┘
       │                                          ↓
       │                              ┌───────────────────┐
       │  TTS Audio (base64)          │  VoiceConsumer    │
       └──────────────────────────    │  - STT (Whisper)  │
                                       │  - LLM (Ollama)   │
                                       │  - TTS (Piper)    │
                                       └───────────────────┘
```

## Pré-requisitos

### Backend

1. **Python 3.10+** com as seguintes dependências adicionais:
   - `channels==4.0.0`
   - `daphne==4.0.0`
   - `channels-redis==4.1.0`

2. **Redis** (para channel layers):
   ```bash
   # Já está a correr no docker-compose
   # Porta: 6379
   ```

3. **TTS Service** (Piper):
   - URL configurado em `TTS_SERVICE_URL`
   - Exemplo: `http://192.168.1.73:8010/api/tts/`

4. **(Opcional) Whisper STT**:
   - Para STT real, instalar: `pip install openai-whisper`
   - Requer `ffmpeg` no sistema
   - Por agora, o STT está em modo mock (retorna None)

### Frontend

1. **Node.js 18+** e npm
2. **Browser moderno** com suporte a:
   - WebSocket
   - MediaRecorder API
   - Web Audio API
   - getUserMedia API

## Instalação

### 1. Backend: Instalar Dependências

```bash
cd /opt/virtualasistant/backend
pip install -r requirements.txt
```

Ou instalar manualmente:
```bash
pip install channels==4.0.0 daphne==4.0.0 channels-redis==4.1.0
```

### 2. Backend: Verificar Configuração

Ficheiro `config/settings.py` deve ter:

```python
INSTALLED_APPS = [
    'daphne',  # Primeiro!
    # ... outros apps ...
    'channels',
    'assistant',
]

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('localhost', 6379)],
        },
    },
}
```

### 3. Backend: Migrar Base de Dados

```bash
cd /opt/virtualasistant/backend
python manage.py migrate
```

### 4. Backend: Testar ASGI

```bash
# Testar o servidor ASGI localmente (sem Docker)
cd /opt/virtualasistant/backend
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 5. Frontend: Rebuild

```bash
cd /opt/virtualasistant/frontend
npm install
npm run build
```

### 6. Nginx: Reload

```bash
# Dentro do container nginx ou no host
docker exec virtualasistant-nginx-1 nginx -s reload
```

Ou reiniciar o container:
```bash
docker-compose restart nginx
```

### 7. Docker: Rebuild e Restart

```bash
cd /opt/virtualasistant
docker-compose build backend
docker-compose up -d
```

## Configuração do Docker

### docker-compose.yml

Certifica-te que o serviço `backend` usa **Daphne** (ASGI) em vez de Gunicorn (WSGI):

```yaml
services:
  backend:
    # ...
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    # OU (para produção com mais workers):
    # command: daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application
```

**IMPORTANTE**: Channels/Daphne usa **ASGI**, não WSGI. Não usar Gunicorn.

### Redis

O `docker-compose.yml` já tem Redis configurado:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Certificar que o backend consegue aceder ao Redis:
- Hostname: `redis` (no Docker network)
- Porta: `6379`

Se estiveres a correr fora do Docker, usar `localhost:6379`.

## Verificação

### 1. Verificar que o Redis está a correr

```bash
docker ps | grep redis
# ou
redis-cli ping
# Deve retornar: PONG
```

### 2. Verificar que o Backend está a usar ASGI

```bash
docker logs virtualasistant-backend-1 | grep -i daphne
# Deve aparecer logs do Daphne
```

### 3. Verificar configuração Nginx

```bash
docker exec virtualasistant-nginx-1 nginx -t
# Deve retornar: syntax is ok
```

### 4. Testar WebSocket no browser

Abrir DevTools → Console e executar:

```javascript
const ws = new WebSocket('ws://localhost:1080/ws/voice/');
ws.onopen = () => console.log('Connected!');
ws.onerror = (e) => console.error('Error:', e);
```

**Nota**: Vai falhar com código 4001 (não autenticado) se não fizeres login primeiro, mas isso é normal.

## Utilização

### 1. Fazer Login

Navegar para `http://localhost:1080/login` e fazer login.

### 2. Aceder à Página de Conversa

Clicar no menu lateral: **📞 Conversa**

Ou navegar diretamente: `http://localhost:1080/conversation`

### 3. Iniciar Conversa

1. Clicar em **"Ligar"**
2. Permitir acesso ao microfone (popup do browser)
3. Falar naturalmente
4. Ver a transcrição em tempo real
5. Ouvir a resposta do Jarvas

### 4. Controlos

- **Silenciar Microfone**: Botão 🎤 (vermelho quando muted)
- **Silenciar Som**: Botão 🔊 (vermelho quando muted)
- **Desligar**: Botão "Desligar" (vermelho)

## Troubleshooting

### Erro: WebSocket connection failed

**Causa**: Nginx não está configurado para proxy WebSocket

**Solução**:
```nginx
location /ws/voice/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # ... outros headers ...
}
```

### Erro: Microphone permission denied

**Causa**: Utilizador negou acesso ao microfone

**Solução**:
1. Clicar no ícone do cadeado na barra de endereços
2. Permitir acesso ao microfone
3. Recarregar a página

### Erro: 401 Unauthorized WebSocket

**Causa**: Utilizador não está autenticado

**Solução**: Fazer login primeiro em `/login`

### Erro: STT returns null

**Causa**: STT está em modo mock (não implementado ainda)

**Solução**:
1. Instalar Whisper: `pip install openai-whisper`
2. Editar `/opt/virtualasistant/backend/assistant/services/stt_service.py`
3. Descomentar a implementação Whisper
4. Reiniciar backend

### Erro: TTS audio não toca

**Causas possíveis**:
1. TTS service não está disponível
2. Browser não suporta formato de áudio
3. Som está silenciado

**Soluções**:
1. Verificar `TTS_SERVICE_URL` nas settings
2. Testar endpoint TTS: `curl http://192.168.1.73:8010/api/tts/ -X POST -H "Content-Type: application/json" -d '{"text":"teste"}'`
3. Verificar console do browser para erros
4. Verificar botão 🔊 não está em vermelho

### Erro: Audio chunks not playing smoothly

**Causa**: Gap entre chunks ou decoding issues

**Solução**:
1. Verificar que `AudioContext` está a funcionar
2. Verificar `sampleRate` do MediaRecorder
3. Aumentar `timeslice` no MediaRecorder para chunks maiores
4. Implementar buffer/queue no frontend

### Redis connection error

**Causa**: Redis não está acessível

**Solução**:
```bash
# Verificar se Redis está a correr
docker ps | grep redis

# Testar conexão
redis-cli -h localhost -p 6379 ping

# Verificar variável de ambiente
echo $REDIS_HOST
```

## Monitoring e Logs

### Backend Logs

```bash
# Logs do Django
docker logs -f virtualasistant-backend-1

# Logs específicos
tail -f /opt/virtualasistant/backend/logs/django.log
```

### WebSocket Logs

Logs no console do browser (DevTools → Console):
- `WebSocket connected`
- `Received audio chunk: X bytes`
- `Processing audio: X bytes`
- `Transcript: ...`

### Nginx Logs

```bash
# Access logs
docker logs virtualasistant-nginx-1 | grep "/ws/voice/"

# Error logs
docker exec virtualasistant-nginx-1 cat /var/log/nginx/error.log
```

## Performance

### Latência esperada

- **Captura de áudio**: ~500ms (timeslice)
- **STT**: 1-2s (depende do Whisper)
- **LLM**: 2-5s (depende do Ollama e do modelo)
- **TTS**: 1-2s (depende do Piper)
- **Total**: ~5-10s do fim da fala até ouvir resposta

### Otimizações possíveis

1. **STT streaming**: Usar STT que suporta streaming (e.g., Google STT, Deepgram)
2. **LLM streaming**: Já implementado (deltas em tempo real)
3. **TTS streaming**: Gerar TTS por frases em vez de resposta completa
4. **WebRTC**: Substituir WebSocket por WebRTC para menor latência
5. **GPU**: Usar GPU para Whisper e Ollama

## Segurança

### Produção

1. **HTTPS obrigatório**: WSS em vez de WS
2. **Rate limiting**: Limitar número de conversas por utilizador
3. **Timeout**: Desconectar sessões idle após X minutos
4. **Tamanho de buffer**: Limitar tamanho acumulado de áudio
5. **Validação**: Validar formato de áudio, tamanho de chunks, etc.

### Configuração HTTPS

Nginx já está configurado para HTTPS (porta 1443):

```nginx
server {
    listen 1443 ssl http2;
    server_name virtualassistant.ddns.net;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # ... WebSocket config igual ...
}
```

WebSocket URL no frontend deve ser:
```javascript
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/voice/`;
```

## Próximos Passos

1. **Implementar STT real** (Whisper ou API externa)
2. **Melhorar VAD** (Voice Activity Detection) para detectar fim de frase
3. **TTS streaming** por frases
4. **Suporte a interrupções** (user pode interromper o Jarvas)
5. **Multi-idioma** (alternar entre PT/EN/etc.)
6. **Histórico de conversa** na UI
7. **Gravação opcional** das conversas

## Referências

- [Django Channels Docs](https://channels.readthedocs.io/)
- [Daphne Server](https://github.com/django/daphne)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- Protocolo completo: `VOICE_WEBSOCKET_PROTOCOL.md`

## Suporte

Em caso de problemas:
1. Verificar logs (backend, nginx, browser console)
2. Consultar `VOICE_WEBSOCKET_PROTOCOL.md`
3. Testar componentes individualmente (STT, LLM, TTS)
4. Verificar configuração do Docker e Nginx
















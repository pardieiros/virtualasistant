# Implementação de Streaming SSE para Chat

Este documento descreve a implementação completa do sistema de streaming de respostas do Ollama usando Server-Sent Events (SSE).

## 📋 Resumo

Implementámos um sistema de streaming que permite ao frontend receber as respostas do LLM incrementalmente, token por token, melhorando significativamente a experiência do utilizador.

### Melhorias de Performance

1. **Caching Inteligente:**
   - Base system prompt: cache de 1 hora
   - Contexto do utilizador (HA devices/aliases): cache de 10 minutos
   - Memórias relevantes: cache de 60 segundos com heurística de keywords
   
2. **Otimizações:**
   - Histórico limitado às últimas 12 mensagens
   - Memory search apenas quando relevante (heurística)
   - HA states não são chamados no system prompt (só quando necessário)

3. **Streaming:**
   - Respostas começam a aparecer imediatamente
   - Chunks enviados assim que chegam do Ollama
   - ACTION parsing no final, não enviada ao UI

## 🏗️ Arquitetura

### Backend (Django)

```
┌─────────────────────────────────────────────────┐
│  Client (Browser)                               │
│  ↓                                              │
│  POST /api/chat/stream/                        │
│  ↓                                              │
│  ChatStreamView (views.py)                     │
│  ↓                                              │
│  build_messages() + stream_ollama_chat()       │
│  ↓                                              │
│  Ollama API (stream=True)                      │
│  ↓                                              │
│  SSE Events → Client                           │
│  • event: message (chunks de texto)            │
│  • event: final_text (texto limpo sem ACTION)  │
│  • event: action (ACTION detectada)            │
│  • event: done (stream completo)               │
│  • event: error (erro)                         │
└─────────────────────────────────────────────────┘
```

### Frontend (React)

```
┌─────────────────────────────────────────┐
│  StreamingChat.tsx                      │
│  ↓                                      │
│  useChatStream() hook                  │
│  ↓                                      │
│  fetch() com ReadableStream            │
│  ↓                                      │
│  Parse SSE events                      │
│  ↓                                      │
│  Update UI incrementalmente            │
└─────────────────────────────────────────┘
```

## 📁 Ficheiros Criados/Modificados

### Backend

1. **`backend/assistant/services/prompt_cache.py`** (NOVO)
   - Sistema de caching para prompts e contexto
   - Funções: `get_base_system_prompt_cached()`, `get_user_context_cached()`, `get_relevant_memories_cached()`
   - Cache keys e TTLs configuráveis

2. **`backend/assistant/services/ollama_client.py`** (MODIFICADO)
   - Adicionadas funções:
     - `get_base_system_prompt()` - prompt base estático
     - `get_time_prompt()` - informação temporal
     - `get_user_context_prompt()` - contexto do utilizador
     - `stream_ollama_chat()` - streaming do Ollama com SSE
   - Modificadas funções:
     - `get_system_prompt()` - agora usa cache
     - `build_messages()` - usa cache e limita histórico

3. **`backend/assistant/views.py`** (MODIFICADO)
   - Nova classe `ChatStreamView` com endpoints GET e POST
   - SSE events: chunk, done, action, error, final_text
   - Headers corretos para SSE

4. **`backend/assistant/urls.py`** (MODIFICADO)
   - Nova rota: `path('chat/stream/', ChatStreamView.as_view(), name='chat_stream')`

### Frontend

5. **`frontend/src/hooks/useChatStream.ts`** (NOVO)
   - Hook React para consumir SSE
   - Gestão de estado: messages, isStreaming, error, action
   - Suporte para cancelamento de stream

6. **`frontend/src/components/StreamingChat.tsx`** (NOVO)
   - Componente de exemplo com UI completa
   - Typing indicator animado
   - Display de erros e actions
   - Auto-scroll

### Documentação

7. **`SSE_NGINX_CONFIG.md`** (NOVO)
   - Configurações Nginx necessárias
   - Troubleshooting
   - Exemplos completos

8. **`STREAMING_IMPLEMENTATION.md`** (NOVO - este ficheiro)
   - Documentação completa da implementação

## 🚀 Como Usar

### 1. Backend - Endpoint SSE

#### POST Request (recomendado)

```python
# JavaScript/TypeScript
const response = await fetch('/api/chat/stream/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({
    message: 'Olá, como estás?',
    history: [
      { role: 'user', content: 'Mensagem anterior' },
      { role: 'assistant', content: 'Resposta anterior' }
    ],
    conversation_id: 123  // opcional
  }),
});

const reader = response.body.getReader();
// ... processar stream
```

#### GET Request (simples)

```bash
curl -N -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/chat/stream/?message=Olá"
```

### 2. Frontend - useChatStream Hook

```tsx
import { useChatStream } from '../hooks/useChatStream';

function MyChat() {
  const {
    sendMessage,
    messages,
    isStreaming,
    error,
    action,
    cancelStream,
    currentStreamingMessage,
  } = useChatStream();

  const handleSend = async () => {
    await sendMessage('Qual o estado do tempo?', messages);
  };

  return (
    <div>
      {messages.map((msg, i) => (
        <div key={i}>{msg.content}</div>
      ))}
      
      {isStreaming && currentStreamingMessage && (
        <div>{currentStreamingMessage}<span className="animate-pulse">|</span></div>
      )}
      
      {isStreaming && (
        <button onClick={cancelStream}>Cancelar</button>
      )}
    </div>
  );
}
```

### 3. Nginx - Configuração

Edita `nginx/nginx.conf`:

```nginx
location /api/chat/stream/ {
    proxy_pass http://backend:8000;
    
    # CRÍTICO para SSE
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header X-Accel-Buffering no;
    
    # Timeouts longos
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    
    # Headers
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    add_header Cache-Control 'no-cache';
}
```

## 📊 Formato dos Eventos SSE

### Event: message (chunk)

```
data: {"type": "chunk", "content": "Olá "}

data: {"type": "chunk", "content": "como "}

data: {"type": "chunk", "content": "estás?"}
```

### Event: final_text

Enviado quando há ACTION no texto (texto limpo sem linha ACTION):

```
event: final_text
data: {"text": "Vou ligar o ar condicionado da sala a 22 graus."}
```

### Event: action

Enviado quando ACTION é detectada:

```
event: action
data: {"action": {"tool": "homeassistant_call_service", "args": {...}}}
```

### Event: done

Sinaliza fim do stream:

```
event: done
data: {"finished": true}
```

### Event: error

Enviado em caso de erro:

```
event: error
data: {"error": "Ollama connection failed"}
```

## 🔧 Configuração do Cache

### Django Settings

Adiciona ao `settings.py` se ainda não existir:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}
```

Para produção, considera usar Redis:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'jarvas'
    }
}
```

## 🧪 Testes

### 1. Testar Backend SSE

```bash
# Terminal 1 - Start services
cd /opt/virtualasistant
docker-compose up

# Terminal 2 - Test endpoint
curl -N -X POST http://localhost/api/chat/stream/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá, como estás?"}'
```

Deves ver chunks a chegar incrementalmente.

### 2. Testar Frontend

```bash
cd /opt/virtualasistant/frontend
npm run dev
```

Abre `http://localhost:5173` e testa o componente StreamingChat.

### 3. Testar Cache

```python
# Django shell
python manage.py shell

from assistant.services.prompt_cache import *
from django.contrib.auth.models import User

user = User.objects.first()

# Test 1: Base prompt (deve ser rápido após 1ª chamada)
prompt1 = get_base_system_prompt_cached()
prompt2 = get_base_system_prompt_cached()  # Cache hit

# Test 2: User context (10 min cache)
ctx1 = get_user_context_cached(user)
ctx2 = get_user_context_cached(user)  # Cache hit

# Test 3: Memories (com heurística)
mems1 = get_relevant_memories_cached(user, "lembras-te do meu aniversário?")
mems2 = get_relevant_memories_cached(user, "lembras-te do meu aniversário?")  # Cache hit
mems3 = get_relevant_memories_cached(user, "que horas são?")  # Nenhuma (heurística)
```

## 🐛 Troubleshooting

### Problema: Stream não funciona (tudo chega de uma vez)

**Causa:** Nginx está a bufferizar.

**Solução:**
1. Verifica `nginx.conf` → `proxy_buffering off;`
2. Reinicia Nginx: `docker restart virtualasistant_nginx`
3. Verifica response headers no DevTools

### Problema: Timeout após alguns segundos

**Causa:** Timeouts muito curtos.

**Solução:**
1. Aumenta `proxy_read_timeout` no Nginx
2. Aumenta timeout do Gunicorn: `--timeout 300`

### Problema: Chunks duplicados no UI

**Causa:** Hook está a acumular chunks incorretamente.

**Solução:**
- Verifica que `currentStreamingMessage` é resetado em cada nova mensagem
- Usa key única para cada mensagem no render

### Problema: ACTION aparece no UI

**Causa:** Frontend não está a tratar evento `final_text`.

**Solução:**
- Implementa handler para `event: final_text` no hook
- Substitui `currentStreamingMessage` com texto limpo

## 📈 Performance Esperada

### Antes (sem streaming)

- Tempo até primeira resposta: **5-15 segundos**
- Utilizador vê: loading spinner
- Backend: chama HA states, memórias, sem cache

### Depois (com streaming + cache)

- Tempo até primeiro chunk: **0.5-2 segundos**
- Utilizador vê: resposta a aparecer token por token
- Backend: usa cache, skip desnecessário

### Métricas

```
Cache Hit Rate:
- Base prompt: ~99% (raramente muda)
- User context: ~95% (10 min cache)
- Memories: ~30% (muitas queries únicas)

Latency Improvement:
- First chunk: 5-10x mais rápido
- Perceived performance: melhoria significativa
```

## 🔐 Segurança

1. **Authentication:** Todos os endpoints requerem `IsAuthenticated`
2. **User Isolation:** Queries filtradas por `request.user`
3. **Rate Limiting:** Considera adicionar rate limiting para SSE
4. **Resource Limits:** Stream auto-fecha após timeout configurado

## 🚀 Próximos Passos (Opcional)

1. **WebSocket Alternative:** Para comunicação bidirecional
2. **Retry Logic:** Auto-reconnect no frontend se stream falhar
3. **Progress Indicators:** Mostrar % de tokens gerados
4. **Action Execution:** Executar actions automaticamente no frontend
5. **Voice Output:** TTS incremental dos chunks

## 📚 Referências

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Django StreamingHttpResponse](https://docs.djangoproject.com/en/stable/ref/request-response/#streaminghttpresponse-objects)
- [Ollama API Streaming](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion)
- [Nginx Proxy Buffering](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)

---

**Implementado por:** AI Assistant  
**Data:** 2025-12-18  
**Versão:** 1.0

















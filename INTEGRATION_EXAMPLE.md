# Exemplo de Integração do Streaming Chat

Este documento mostra como integrar o componente `StreamingChat` na aplicação existente.

## Opção 1: Substituir Chat Existente

Se quiseres substituir completamente o chat atual pelo streaming:

### 1. No `App.tsx` ou Router

```tsx
// Importa o novo componente
import StreamingChat from './components/StreamingChat';

// Substitui a rota do chat
<Route path="/chat" element={<StreamingChat />} />
```

### 2. Mantém Chat Antigo como Fallback

```tsx
import Chat from './pages/Chat';
import StreamingChat from './components/StreamingChat';
import { useState } from 'react';

function ChatPage() {
  const [useStreaming, setUseStreaming] = useState(true);
  
  return (
    <div>
      <button onClick={() => setUseStreaming(!useStreaming)}>
        {useStreaming ? 'Usar chat normal' : 'Usar streaming'}
      </button>
      
      {useStreaming ? <StreamingChat /> : <Chat />}
    </div>
  );
}
```

## Opção 2: Adicionar Streaming ao Chat Existente

Se quiseres manter o componente `Chat.tsx` existente mas adicionar streaming:

### 1. Lê o Chat.tsx Atual

```bash
cat /opt/virtualasistant/frontend/src/pages/Chat.tsx
```

### 2. Modifica para Usar Hook

```tsx
// Em Chat.tsx
import { useChatStream } from '../hooks/useChatStream';

export default function Chat() {
  // Substitui useState por useChatStream
  const {
    sendMessage,
    messages,
    isStreaming,
    error,
    action,
    currentStreamingMessage,
  } = useChatStream();

  // Resto do código...
  const handleSend = async () => {
    await sendMessage(inputMessage, messages);
    setInputMessage('');
  };

  // Renderiza mensagens + streaming message
  return (
    <div>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      
      {isStreaming && currentStreamingMessage && (
        <MessageBubble 
          message={{ role: 'assistant', content: currentStreamingMessage }} 
          isStreaming={true}
        />
      )}
      
      {isStreaming && !currentStreamingMessage && (
        <TypingIndicator />
      )}
    </div>
  );
}
```

## Opção 3: Toggle no Settings

Permite ao utilizador escolher entre streaming e normal:

### 1. Adiciona Setting

```tsx
// Em Settings.tsx
const [streamingEnabled, setStreamingEnabled] = useState(() => {
  return localStorage.getItem('streaming_enabled') === 'true';
});

const handleToggleStreaming = (enabled: boolean) => {
  setStreamingEnabled(enabled);
  localStorage.setItem('streaming_enabled', enabled ? 'true' : 'false');
};

// UI
<div className="setting-item">
  <label>
    <input 
      type="checkbox" 
      checked={streamingEnabled} 
      onChange={(e) => handleToggleStreaming(e.target.checked)} 
    />
    Ativar respostas em tempo real (streaming)
  </label>
  <p className="text-sm text-gray-600">
    Quando ativado, as respostas do assistente aparecem token por token.
  </p>
</div>
```

### 2. No Chat.tsx

```tsx
import { useChatStream } from '../hooks/useChatStream';
import { useState } from 'react';

export default function Chat() {
  const streamingEnabled = localStorage.getItem('streaming_enabled') === 'true';
  
  // Use streaming hook se ativado
  const streamingChat = useChatStream();
  
  // Use estado normal se desativado
  const [normalMessages, setNormalMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (message: string) => {
    if (streamingEnabled) {
      await streamingChat.sendMessage(message, streamingChat.messages);
    } else {
      // Lógica normal (fetch sem streaming)
      setLoading(true);
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      });
      const data = await response.json();
      setNormalMessages(prev => [...prev, 
        { role: 'user', content: message },
        { role: 'assistant', content: data.reply }
      ]);
      setLoading(false);
    }
  };

  const messages = streamingEnabled ? streamingChat.messages : normalMessages;
  const isLoading = streamingEnabled ? streamingChat.isStreaming : loading;
  
  return (
    // ... UI com messages e isLoading
  );
}
```

## Opção 4: Migração Gradual (Recomendado)

### Fase 1: Adicionar Nova Rota de Teste

```tsx
// App.tsx
<Route path="/chat" element={<Chat />} />
<Route path="/chat-stream" element={<StreamingChat />} />
```

Agora tens:
- `/chat` - Chat original (mantém funcional)
- `/chat-stream` - Novo streaming chat (para testar)

### Fase 2: Adicionar Link de Teste

```tsx
// No Dashboard ou Settings
<Link to="/chat-stream" className="btn-primary">
  🚀 Experimentar novo chat com streaming
</Link>
```

### Fase 3: Monitorizar & Ajustar

- Recolhe feedback dos utilizadores
- Ajusta UI/UX conforme necessário
- Corrige bugs específicos

### Fase 4: Tornar Padrão

```tsx
// Depois de testado, substitui rota principal
<Route path="/chat" element={<StreamingChat />} />
<Route path="/chat-legacy" element={<Chat />} /> {/* fallback */}
```

## Exemplo Completo de Integração

### Chat.tsx (versão híbrida)

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { useChatStream } from '../hooks/useChatStream';
import { useAuth } from '../context/AuthContext';

export default function Chat() {
  const { user } = useAuth();
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Use streaming hook
  const {
    sendMessage,
    messages,
    isStreaming,
    error,
    action,
    cancelStream,
    currentStreamingMessage,
  } = useChatStream();

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamingMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isStreaming) return;

    const msg = inputMessage.trim();
    setInputMessage('');
    await sendMessage(msg, messages);
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="bg-white shadow-sm p-4 border-b">
        <h1 className="text-xl font-semibold">Chat com Jarvas</h1>
        {isStreaming && (
          <p className="text-sm text-blue-600 flex items-center gap-2">
            <span className="animate-pulse">●</span>
            A escrever...
          </p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && currentStreamingMessage && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg p-3 bg-gray-100 text-gray-800">
              <p className="whitespace-pre-wrap">{currentStreamingMessage}</p>
              <span className="inline-block w-2 h-4 ml-1 bg-gray-800 animate-pulse" />
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {isStreaming && !currentStreamingMessage && (
          <div className="flex justify-start">
            <div className="rounded-lg p-3 bg-gray-100">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error display */}
      {error && (
        <div className="mx-4 mb-2 p-3 bg-red-100 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Escreve a tua mensagem..."
            disabled={isStreaming}
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          
          {isStreaming ? (
            <button
              type="button"
              onClick={cancelStream}
              className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
            >
              Cancelar
            </button>
          ) : (
            <button
              type="submit"
              disabled={!inputMessage.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Enviar
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
```

## Testes Antes de Deploy

### 1. Teste Local

```bash
# Terminal 1: Backend
cd /opt/virtualasistant
docker-compose up backend

# Terminal 2: Frontend
cd /opt/virtualasistant/frontend
npm run dev

# Browser: http://localhost:5173/chat-stream
```

### 2. Teste com Backend Real

```bash
# Build e restart tudo
cd /opt/virtualasistant
docker-compose down
docker-compose up --build
```

### 3. Teste de Stress

```bash
# Abrir múltiplos tabs no browser
# Enviar mensagens simultâneas
# Verificar que não há race conditions
```

## Checklist de Deploy

- [ ] Nginx configurado com `proxy_buffering off`
- [ ] Backend com cache ativado (locmem ou redis)
- [ ] Frontend buildado com novo hook
- [ ] Testes de SSE funcionais
- [ ] Logs a monitorizar (Django, Nginx, Ollama)
- [ ] Rollback plan (manter endpoint antigo `/api/chat/`)
- [ ] Documentação atualizada

## Notas Importantes

1. **Compatibilidade:** O endpoint antigo `/api/chat/` continua funcional. Podes manter ambos.
2. **Fallback:** Se SSE falhar, podes facilmente fazer fallback para o endpoint normal.
3. **Mobile:** SSE funciona bem em mobile, mas testa especialmente no iOS Safari.
4. **Timeouts:** Ajusta conforme necessário (300s é um bom padrão).

---

Boa sorte com a integração! 🚀



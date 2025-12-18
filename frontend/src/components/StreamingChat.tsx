/**
 * Example component demonstrating SSE streaming chat.
 * 
 * This component uses the useChatStream hook to send messages
 * and display responses incrementally as they arrive from the LLM.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useChatStream } from '../hooks/useChatStream';

const StreamingChat: React.FC = () => {
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const {
    sendMessage,
    messages,
    isStreaming,
    error,
    action,
    cancelStream,
    currentStreamingMessage,
  } = useChatStream();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamingMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || isStreaming) {
      return;
    }

    const message = inputMessage.trim();
    setInputMessage('');
    
    // Send message with current conversation history
    await sendMessage(message, messages);
  };

  const handleCancel = () => {
    cancelStream();
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Streaming Chat</h1>
        <p className="text-sm text-gray-600">
          Respostas em tempo real com Server-Sent Events
        </p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 bg-gray-50 rounded-lg p-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-800 shadow-sm border border-gray-200'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* Streaming Message (being typed) */}
        {isStreaming && currentStreamingMessage && (
          <div className="flex justify-start">
            <div className="max-w-[70%] rounded-lg p-3 bg-white text-gray-800 shadow-sm border border-gray-200">
              <p className="whitespace-pre-wrap">{currentStreamingMessage}</p>
              <span className="inline-block w-2 h-4 ml-1 bg-gray-800 animate-pulse" />
            </div>
          </div>
        )}

        {/* Typing Indicator (no content yet) */}
        {isStreaming && !currentStreamingMessage && (
          <div className="flex justify-start">
            <div className="rounded-lg p-3 bg-white shadow-sm border border-gray-200">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          <p className="font-semibold">Erro:</p>
          <p>{error}</p>
        </div>
      )}

      {/* Action Display (for debugging) */}
      {action && (
        <div className="mb-4 p-3 bg-blue-100 border border-blue-400 text-blue-700 rounded-lg">
          <p className="font-semibold">Action detectada:</p>
          <pre className="text-xs mt-2 overflow-x-auto">
            {JSON.stringify(action, null, 2)}
          </pre>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Escreve a tua mensagem..."
          disabled={isStreaming}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        
        {isStreaming ? (
          <button
            type="button"
            onClick={handleCancel}
            className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
          >
            Cancelar
          </button>
        ) : (
          <button
            type="submit"
            disabled={!inputMessage.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Enviar
          </button>
        )}
      </form>

      {/* Info Footer */}
      <div className="mt-4 text-center text-xs text-gray-500">
        {isStreaming ? (
          <p>A receber resposta em tempo real... ⚡</p>
        ) : messages.length > 0 ? (
          <p>{messages.length} mensagens na conversa</p>
        ) : (
          <p>Envia uma mensagem para começar</p>
        )}
      </div>
    </div>
  );
};

export default StreamingChat;


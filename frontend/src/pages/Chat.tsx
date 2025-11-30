import { useState, useEffect, useRef } from 'react';
import { chatAPI } from '../api/client';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { speak, stopSpeaking } from '../utils/speech';
import { usePusher } from '../hooks/usePusher';
import { getUserIdFromToken } from '../utils/jwt';
import type { ChatMessage } from '../types';

const Chat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { transcript, isListening, startListening, stopListening } = useSpeechRecognition();

  const userId = getUserIdFromToken();

  useEffect(() => {
    if (transcript && !isListening) {
      setInput(transcript);
    }
  }, [transcript, isListening]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  usePusher(userId || 0, (event, data) => {
    if (event === 'assistant-message') {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.message },
      ]);
      if (voiceEnabled) {
        speak(data.message, voiceEnabled);
      }
      setLoading(false);
    }
  });

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chatAPI.send(userMessage, messages);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply },
      ]);

      if (voiceEnabled) {
        speak(response.reply, voiceEnabled);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleMicClick = () => {
    if (isListening) {
      stopListening();
    } else {
      stopSpeaking();
      startListening();
    }
  };

  return (
    <div className="h-full flex flex-col bg-dark-charcoal">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-text-medium mt-20">
            <div className="text-6xl mb-4">🤖</div>
            <h2 className="text-2xl font-semibold text-primary-gold mb-2">
              Your Personal Assistant
            </h2>
            <p>Ask me anything or use voice input to get started.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-primary-gold text-dark-charcoal'
                  : 'bg-dark-warm-gray text-text-light'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-warm-gray rounded-lg px-4 py-3">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-dark-warm-gray p-4 bg-dark-warm-gray">
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type your message or use voice input..."
              className="input-field w-full resize-none min-h-[60px] max-h-32"
              rows={2}
            />
            {isListening && (
              <div className="mt-2 text-sm text-primary-gold flex items-center gap-2">
                <span className="w-2 h-2 bg-status-error rounded-full animate-pulse"></span>
                Listening...
              </div>
            )}
          </div>
          <button
            onClick={handleMicClick}
            className={`btn-secondary p-3 ${
              isListening ? 'bg-status-error hover:bg-status-error/80' : ''
            }`}
            title={isListening ? 'Stop listening' : 'Start voice input'}
          >
            🎤
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="btn-primary px-6 py-3 disabled:opacity-50"
          >
            Send
          </button>
        </div>
        <div className="mt-2 flex items-center gap-2 text-sm text-text-medium">
          <button
            onClick={() => {
              setVoiceEnabled(!voiceEnabled);
              if (!voiceEnabled) {
                stopSpeaking();
              }
            }}
            className={`px-3 py-1 rounded ${
              voiceEnabled
                ? 'bg-primary-gold/20 text-primary-gold'
                : 'bg-dark-warm-gray text-text-medium'
            }`}
          >
            🔊 {voiceEnabled ? 'Voice ON' : 'Voice OFF'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;


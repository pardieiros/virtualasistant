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
  const [continuousMode, setContinuousMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { transcript, isListening, startListening, stopListening } = useSpeechRecognition();

  const userId = getUserIdFromToken();

  useEffect(() => {
    if (transcript && !isListening && !continuousMode) {
      setInput(transcript);
    }
  }, [transcript, isListening, continuousMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  usePusher(userId || 0, async (event, data) => {
    if (event === 'assistant-message') {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.message },
      ]);
      setLoading(false);
      
      if (voiceEnabled) {
        await speak(data.message, voiceEnabled);
        // After assistant finishes speaking, restart listening if in continuous mode
        if (continuousMode && !isListening) {
          setTimeout(() => {
            startListening(handleVoiceInput);
          }, 500);
        }
      } else if (continuousMode && !isListening) {
        // If voice is disabled but continuous mode is on, restart listening immediately
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 500);
      }
    }
  });

  const handleVoiceInput = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage = text.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chatAPI.send(userMessage, messages);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply },
      ]);

      if (voiceEnabled) {
        await speak(response.reply, voiceEnabled);
        // After assistant finishes speaking, restart listening if in continuous mode
        if (continuousMode && !isListening) {
          setTimeout(() => {
            startListening(handleVoiceInput);
          }, 500);
        }
      } else if (continuousMode && !isListening) {
        // If voice is disabled but continuous mode is on, restart listening immediately
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 500);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
      // Restart listening even on error if in continuous mode
      if (continuousMode && !isListening) {
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

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
        await speak(response.reply, voiceEnabled);
        // After assistant finishes speaking, restart listening if in continuous mode
        if (continuousMode && !isListening) {
          setTimeout(() => {
            startListening(handleVoiceInput);
          }, 500);
        }
      } else if (continuousMode && !isListening) {
        // If voice is disabled but continuous mode is on, restart listening immediately
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 500);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
      // Restart listening even on error if in continuous mode
      if (continuousMode && !isListening) {
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleMicClick = () => {
    if (continuousMode) {
      // Stop continuous mode
      setContinuousMode(false);
      stopListening();
      stopSpeaking();
    } else {
      // Start continuous mode
      setContinuousMode(true);
      stopSpeaking();
      startListening(handleVoiceInput);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-dark-charcoal via-dark-charcoal to-dark-warm-gray/30">
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-text-medium mt-10 md:mt-20">
            <img 
              src="/personal_assistance_logo_nobg.png" 
              alt="Personal Assistant Logo" 
              className="h-24 w-24 md:h-32 md:w-32 object-contain mx-auto mb-4 drop-shadow-lg"
            />
            <h2 className="text-xl md:text-2xl font-semibold bg-gradient-to-r from-primary-gold to-primary-gold-soft bg-clip-text text-transparent mb-2">
              Your Personal Assistant
            </h2>
            <p className="text-sm md:text-base">Ask me anything or use voice input to get started.</p>
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
              className={`max-w-[85%] md:max-w-3xl rounded-xl px-4 py-3 shadow-lg ${
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-primary-gold to-primary-gold-soft text-dark-charcoal'
                  : 'bg-dark-warm-gray/90 backdrop-blur-sm text-text-light border border-primary-gold/10'
              }`}
            >
              <p className="whitespace-pre-wrap text-sm md:text-base">{msg.content}</p>
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

      <div className="border-t border-primary-gold/20 p-3 md:p-4 bg-gradient-to-t from-dark-warm-gray to-dark-charcoal shadow-2xl">
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
              className="input-field w-full resize-none min-h-[50px] md:min-h-[60px] max-h-32 text-sm md:text-base"
              rows={2}
              disabled={continuousMode}
            />
            {(isListening || continuousMode) && (
              <div className="mt-2 text-sm text-primary-gold flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full animate-pulse ${
                  continuousMode ? 'bg-primary-gold' : 'bg-status-error'
                }`}></span>
                {continuousMode ? 'Continuous conversation active...' : 'Listening...'}
              </div>
            )}
          </div>
          <button
            onClick={handleMicClick}
            className={`btn-secondary p-3 transition-all ${
              continuousMode
                ? 'bg-primary-gold hover:bg-primary-gold-soft text-dark-charcoal animate-pulse'
                : isListening
                ? 'bg-status-error hover:bg-status-error/80'
                : ''
            }`}
            title={continuousMode ? 'Stop continuous conversation' : isListening ? 'Stop listening' : 'Start continuous conversation'}
          >
            {continuousMode ? '🎙️' : '🎤'}
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || continuousMode}
            className="btn-primary px-4 md:px-6 py-3 disabled:opacity-50 text-sm md:text-base"
          >
            Send
          </button>
        </div>
        <div className="mt-2 flex items-center gap-2 text-sm text-text-medium flex-wrap">
          <button
            onClick={() => {
              setVoiceEnabled(!voiceEnabled);
              if (!voiceEnabled) {
                stopSpeaking();
              }
            }}
            className={`px-3 py-1 rounded transition-colors ${
              voiceEnabled
                ? 'bg-primary-gold/20 text-primary-gold border border-primary-gold/30'
                : 'bg-dark-warm-gray text-text-medium border border-dark-warm-gray'
            }`}
          >
            🔊 {voiceEnabled ? 'Voice ON' : 'Voice OFF'}
          </button>
          {continuousMode && (
            <div className="px-3 py-1 rounded bg-primary-gold/20 text-primary-gold border border-primary-gold/30">
              🎙️ Continuous Mode
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chat;


import { useState, useEffect, useRef } from 'react';
import { chatAPI } from '../api/client';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { speak, stopSpeaking } from '../utils/speech';
import { usePusher } from '../hooks/usePusher';
import { getUserIdFromToken } from '../utils/jwt';
import type { ChatMessage } from '../types';
import VoiceModal from '../components/VoiceModal';

const Chat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [continuousMode, setContinuousMode] = useState(false);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const voiceModalOpenRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { transcript, isListening, startListening, stopListening } = useSpeechRecognition();

  const userId = getUserIdFromToken();

  // Keep ref in sync with state
  useEffect(() => {
    voiceModalOpenRef.current = voiceModalOpen;
  }, [voiceModalOpen]);

  useEffect(() => {
    if (transcript && !isListening && !continuousMode) {
      setInput(transcript);
    }
  }, [transcript, isListening, continuousMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  usePusher(userId || 0, async (event, data) => {
    console.log('[Chat] Pusher event received:', event, data);
    
    if (event === 'assistant-message') {
      const messageType = data.type || 'normal';
      const status = data.status || 'completed';
      
      console.log('[Chat] Processing assistant-message:', { messageType, status, message: data.message });
      
      if (messageType === 'search_status' && status === 'searching') {
        console.log('[Chat] Handling search_status searching');
        // Replace or add searching message
        setMessages((prev) => {
          // Remove any existing searching message
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.content.includes('🔍 A pesquisar'))
          );
          return [...filtered, { role: 'assistant', content: data.message, isSearching: true }];
        });
        setLoading(true);
        
        // Only play audio if VoiceModal is not open (VoiceModal will handle audio when open)
        // Use ref to get current value (callback may have stale closure)
        // Play audio if provided and available
        // audio_available === false means audio was removed due to size limit
        if (voiceEnabled && !voiceModalOpenRef.current && data.audio && data.audio_format && data.audio_available !== false) {
          try {
            const { playAudioFromBase64 } = await import('../utils/speech');
            await playAudioFromBase64(data.audio, data.audio_format).catch(() => {
              // If audio playback fails (e.g., autoplay blocked), fallback to TTS
              return speak(data.message, voiceEnabled);
            });
          } catch (error) {
            console.error('Error playing audio from Pusher:', error);
            // Fallback to generating audio
            await speak(data.message, voiceEnabled);
          }
        } else if (voiceEnabled && !voiceModalOpenRef.current) {
          // Audio not available - generate locally
          await speak(data.message, voiceEnabled);
        }
      } else if (messageType === 'search_response' && status === 'completed') {
        console.log('[Chat] Handling search_response completed, message:', data.message);
        // Replace searching message with final response
        setMessages((prev) => {
          // Remove searching message and add final response
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.isSearching)
          );
          const newMessages = [...filtered, { role: 'assistant' as const, content: data.message }];
          console.log('[Chat] Updated messages after search_response:', newMessages);
          return newMessages;
        });
        setLoading(false);
        
        // Only play audio if VoiceModal is not open (VoiceModal will handle audio when open)
        // Use ref to get current value (callback may have stale closure)
        if (voiceEnabled && !voiceModalOpenRef.current) {
          // If audio is provided from backend and available, use it; otherwise generate it
          // audio_available === false means audio was removed due to size limit
          if (data.audio && data.audio_format && data.audio_available !== false) {
            try {
              const { playAudioFromBase64 } = await import('../utils/speech');
              await playAudioFromBase64(data.audio, data.audio_format).catch(() => {
                // If audio playback fails (e.g., autoplay blocked), fallback to TTS
                return speak(data.message, voiceEnabled);
              });
            } catch (error) {
              console.error('Error playing audio from Pusher:', error);
              // Fallback to generating audio
              await speak(data.message, voiceEnabled);
            }
          } else {
            // Audio not available or too large - generate locally
            await speak(data.message, voiceEnabled);
          }
          // After assistant finishes speaking, restart listening if in continuous mode
          if (continuousMode && !isListening) {
            setTimeout(() => {
              startListening(handleVoiceInput);
            }, 500);
          }
        } else if (continuousMode && !isListening && !voiceModalOpenRef.current) {
          // Only restart listening if VoiceModal is not open
          setTimeout(() => {
            startListening(handleVoiceInput);
          }, 500);
        }
      } else if (messageType === 'search_status' && (status === 'no_results' || status === 'error')) {
        // Replace searching message with error/no results message
        setMessages((prev) => {
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.isSearching)
          );
          return [...filtered, { role: 'assistant', content: data.message }];
        });
        setLoading(false);
      } else {
        console.log('[Chat] Handling normal message:', data.message);
        // Normal message - check if already exists to avoid duplicates
        setMessages((prev) => {
          // Check if this message was already added
          const alreadyExists = prev.some(
            (msg) => msg.role === 'assistant' && msg.content === data.message
          );
          if (alreadyExists) {
            console.log('[Chat] Message already exists, skipping Pusher message');
            return prev;
          }
          const newMessages = [...prev, { role: 'assistant' as const, content: data.message }];
          console.log('[Chat] Updated messages after normal message:', newMessages);
          return newMessages;
        });
        setLoading(false);
        
        // Only play audio if VoiceModal is not open (VoiceModal will handle audio when open)
        // Use ref to get current value (callback may have stale closure)
        if (voiceEnabled && !voiceModalOpenRef.current) {
          // If audio is provided from backend and available, use it; otherwise generate it
          // audio_available === false means audio was removed due to size limit
          if (data.audio && data.audio_format && data.audio_available !== false) {
            try {
              const { playAudioFromBase64 } = await import('../utils/speech');
              await playAudioFromBase64(data.audio, data.audio_format).catch(() => {
                // If audio playback fails (e.g., autoplay blocked), fallback to TTS
                return speak(data.message, voiceEnabled);
              });
            } catch (error) {
              console.error('Error playing audio from Pusher:', error);
              // Fallback to generating audio
              await speak(data.message, voiceEnabled);
            }
          } else {
            // Audio not available or too large - generate locally
            await speak(data.message, voiceEnabled);
          }
          // After assistant finishes speaking, restart listening if in continuous mode
          if (continuousMode && !isListening) {
            setTimeout(() => {
              startListening(handleVoiceInput);
            }, 500);
          }
        } else if (continuousMode && !isListening && !voiceModalOpenRef.current) {
          // If voice is disabled but continuous mode is on, restart listening immediately
          // Only if VoiceModal is not open
          setTimeout(() => {
            startListening(handleVoiceInput);
          }, 500);
        }
      }
    } else {
      console.log('[Chat] Received non-assistant-message event:', event);
    }
  });

  const handleVoiceInput = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage = text.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await chatAPI.send(userMessage, messages);
      
      // Check if search is in progress
      if (response.search_in_progress) {
        // Don't add message yet, wait for Pusher update
        setLoading(true);
      } else if (response.via_pusher) {
        // Message is coming via Pusher - don't add from HTTP response
        // Just keep loading state, Pusher will handle the message
        console.log('[Chat] Message will come via Pusher, skipping HTTP response');
        setLoading(true);
      } else if (response.reply) {
        // Message not via Pusher - add from HTTP response
        // But check if it was already added via Pusher (race condition)
        const replyText = response.reply; // TypeScript now knows this is not null
        let messageWasAdded = false;
        setMessages((prev) => {
          // Check if this message was already added via Pusher
          const alreadyExists = prev.some(
            (msg) => msg.role === 'assistant' && msg.content === replyText
          );
          if (alreadyExists) {
            console.log('[Chat] Message already exists from Pusher, skipping HTTP response');
            return prev;
          }
          messageWasAdded = true;
          return [...prev, { role: 'assistant' as const, content: replyText }];
        });
        
        // Only speak if we actually added the message (not from Pusher)
        if (messageWasAdded && voiceEnabled) {
          await speak(replyText, voiceEnabled);
        }
      }

      // After assistant finishes speaking, restart listening if in continuous mode
      if (continuousMode && !isListening && !response.search_in_progress) {
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 500);
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
      
      // Check if search is in progress
      if (response.search_in_progress) {
        // Don't add message yet, wait for Pusher update
        setLoading(true);
      } else if (response.via_pusher) {
        // Message is coming via Pusher - don't add from HTTP response
        // Just keep loading state, Pusher will handle the message
        console.log('[Chat] Message will come via Pusher, skipping HTTP response');
        setLoading(true);
      } else if (response.reply) {
        // Message not via Pusher - add from HTTP response
        // But check if it was already added via Pusher (race condition)
        const replyText = response.reply; // TypeScript now knows this is not null
        let messageWasAdded = false;
        setMessages((prev) => {
          // Check if this message was already added via Pusher
          const alreadyExists = prev.some(
            (msg) => msg.role === 'assistant' && msg.content === replyText
          );
          if (alreadyExists) {
            console.log('[Chat] Message already exists from Pusher, skipping HTTP response');
            return prev;
          }
          messageWasAdded = true;
          return [...prev, { role: 'assistant' as const, content: replyText }];
        });
        
        // Only speak if we actually added the message (not from Pusher)
        if (messageWasAdded && voiceEnabled) {
          await speak(replyText, voiceEnabled);
        }
      }

      // After assistant finishes speaking, restart listening if in continuous mode
      if (continuousMode && !isListening && !response.search_in_progress) {
        setTimeout(() => {
          startListening(handleVoiceInput);
        }, 500);
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
            {(isListening || continuousMode) && !voiceModalOpen && (
              <div className="mt-2 text-sm text-primary-gold flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full animate-pulse ${
                  continuousMode ? 'bg-primary-gold' : 'bg-status-error'
                }`}></span>
                {continuousMode ? 'Continuous conversation active...' : 'Listening...'}
              </div>
            )}
          </div>
          <button
            onClick={() => setVoiceModalOpen(true)}
            className="btn-secondary p-3 transition-all hover:bg-primary-gold/10 hover:text-primary-gold"
            title="Abrir modal de voz"
          >
            🎙️
          </button>
          <button
            onClick={handleMicClick}
            className={`btn-secondary p-3 transition-all ${
              continuousMode
                ? 'bg-primary-gold hover:bg-primary-gold-soft text-dark-charcoal animate-pulse'
                : isListening
                ? 'bg-status-error hover:bg-status-error/80'
                : ''
            }`}
            title={continuousMode ? 'Parar conversa contínua' : isListening ? 'Parar de ouvir' : 'Iniciar conversa contínua'}
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

      {/* Voice Modal */}
      <VoiceModal
        isOpen={voiceModalOpen}
        onClose={() => setVoiceModalOpen(false)}
        onTranscript={(text) => {
          // Add transcript to messages if needed
          setMessages((prev) => [...prev, { role: 'user', content: text }]);
        }}
      />
    </div>
  );
};

export default Chat;


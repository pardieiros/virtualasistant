import { useState, useEffect, useRef, useCallback } from 'react';
import { useVoiceRecognition } from '../hooks/useVoiceRecognition';
import { speak, stopSpeaking } from '../utils/speech';
import { chatAPI } from '../api/client';
import { usePusher } from '../hooks/usePusher';
import { getUserIdFromToken } from '../utils/jwt';
import type { ChatMessage } from '../types';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscript: (text: string) => void;
}

const VoiceModal = ({ isOpen, onClose, onTranscript }: VoiceModalProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [conversationActive, setConversationActive] = useState(false);
  const { transcript, isListening, error, audioLevel, startListening, stopListening } = useVoiceRecognition();
  const userId = getUserIdFromToken();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isProcessingRef = useRef<boolean>(false); // Flag to prevent duplicate processing
  const messagesRef = useRef<ChatMessage[]>([]); // Ref to track current messages
  const isOpenRef = useRef(isOpen); // Ref to track if modal is open
  
  // Keep ref in sync with prop
  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    messagesRef.current = messages; // Keep ref in sync
  }, [messages]);

  const handleVoiceInputRef = useRef<(text: string) => Promise<void>>();

  const handleVoiceInput = useCallback(async (text: string) => {
    if (!text.trim()) {
      return;
    }
    
    // Prevent duplicate processing
    if (isProcessingRef.current) {
      return;
    }
    
    isProcessingRef.current = true;
    setLoading(true);

    const userMessage = text.trim();
    
    // Add user message to state
    setMessages((prev) => {
      const newMessages = [...prev, { role: 'user' as const, content: userMessage }];
      onTranscript(userMessage);
      return newMessages;
    });
    
    try {
      // Get current messages for context
      const currentMessages = messagesRef.current;
      // Send to backend
      const response = await chatAPI.send(userMessage, currentMessages);
      
      // Check if search is in progress
      if (response.search_in_progress) {
        // Don't add message yet, wait for Pusher update
        setLoading(true);
      } else if (response.via_pusher) {
        // Message is coming via Pusher - don't add from HTTP response
        // Just keep loading state, Pusher will handle the message
        console.log('[VoiceModal] Message will come via Pusher, skipping HTTP response');
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
            console.log('[VoiceModal] Message already exists from Pusher, skipping HTTP response');
            return prev;
          }
          messageWasAdded = true;
          return [...prev, { role: 'assistant' as const, content: replyText }];
        });
        
        // Only speak if we actually added the message (not from Pusher)
        if (messageWasAdded && voiceEnabled) {
          speak(replyText, voiceEnabled).then(() => {
            // After assistant finishes speaking, restart listening if conversation is active
            if (conversationActive && !isListening) {
              setTimeout(() => {
                handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
              }, 500);
            }
          });
        } else if (conversationActive && !isListening) {
          setTimeout(() => {
            handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
          }, 500);
        }
      } else if (conversationActive && !isListening) {
        // If no reply and conversation is active, restart listening
        setTimeout(() => {
          handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
        }, 500);
      }
    } catch (error: any) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant' as const, content: 'Desculpa, encontrei um erro. Por favor tenta novamente.' },
      ]);
      // Restart listening even on error if conversation is active
      if (conversationActive && !isListening) {
        setTimeout(() => {
          handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
        }, 1000);
      }
    } finally {
      setLoading(false);
      isProcessingRef.current = false;
    }
  }, [voiceEnabled, conversationActive, isListening, startListening, onTranscript]);

  // Update ref when function changes
  useEffect(() => {
    handleVoiceInputRef.current = handleVoiceInput;
  }, [handleVoiceInput]);

  // Stable callback for Pusher messages
  const handlePusherMessage = useCallback(async (event: string, data: any) => {
    console.log('[VoiceModal] Pusher event received:', event, data);
    
    if (event === 'assistant-message') {
      const messageType = data.type || 'normal';
      const status = data.status || 'completed';
      
      console.log('[VoiceModal] Processing assistant-message:', { messageType, status, message: data.message });
      
      if (messageType === 'search_status' && status === 'searching') {
        console.log('[VoiceModal] Handling search_status searching');
        // Replace or add searching message
        setMessages((prev) => {
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.content.includes('🔍 A pesquisar'))
          );
          return [...filtered, { role: 'assistant', content: data.message }];
        });
        setLoading(true);
        isProcessingRef.current = true; // Keep processing flag true during search
        
        // Only play audio if modal is actually open (use ref to get current value)
        if (voiceEnabled && isOpenRef.current && data.audio && data.audio_format && data.audio_available !== false) {
          try {
            const { playAudioFromBase64 } = await import('../utils/speech');
            await playAudioFromBase64(data.audio, data.audio_format);
          } catch (error) {
            console.error('Error playing audio from Pusher:', error);
            // Fallback to generating audio
            await speak(data.message, voiceEnabled);
          }
        } else if (voiceEnabled && isOpenRef.current) {
          // Audio not available - generate locally
          await speak(data.message, voiceEnabled);
        }
      } else if (messageType === 'search_response' && status === 'completed') {
        console.log('[VoiceModal] Handling search_response completed, message:', data.message);
        // Replace searching message with final response
        setMessages((prev) => {
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.content.includes('🔍 A pesquisar'))
          );
          // Check if this message was already added
          const alreadyExists = filtered.some(
            (msg) => msg.role === 'assistant' && msg.content === data.message
          );
          if (alreadyExists) {
            console.log('[VoiceModal] Message already exists, skipping');
            return filtered;
          }
          const newMessages = [...filtered, { role: 'assistant' as const, content: data.message }];
          console.log('[VoiceModal] Updated messages after search_response:', newMessages);
          return newMessages;
        });
        setLoading(false);
        isProcessingRef.current = false; // Reset processing flag
        
        // Only play audio if modal is actually open (use ref to get current value)
        if (voiceEnabled && isOpenRef.current) {
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
        }
        // After assistant finishes speaking, restart listening if conversation is active
        if (conversationActive && !isListening) {
          setTimeout(() => {
            handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
          }, 500);
        }
      } else if (messageType === 'search_status' && (status === 'no_results' || status === 'error')) {
        // Replace searching message with error/no results message
        setMessages((prev) => {
          const filtered = prev.filter(
            (msg) => !(msg.role === 'assistant' && msg.content.includes('🔍 A pesquisar'))
          );
          return [...filtered, { role: 'assistant', content: data.message }];
        });
        setLoading(false);
        isProcessingRef.current = false;
      } else {
        console.log('[VoiceModal] Handling normal message:', data.message);
        // Normal message - check if already exists to avoid duplicates
        setMessages((prev) => {
          // Check if this message was already added
          const alreadyExists = prev.some(
            (msg) => msg.role === 'assistant' && msg.content === data.message
          );
          if (alreadyExists) {
            console.log('[VoiceModal] Message already exists, skipping Pusher message');
            return prev;
          }
          const newMessages = [...prev, { role: 'assistant' as const, content: data.message }];
          console.log('[VoiceModal] Updated messages after normal message:', newMessages);
          return newMessages;
        });
        setLoading(false);
        isProcessingRef.current = false; // Reset processing flag
        
        // Only play audio if modal is actually open (use ref to get current value)
        if (voiceEnabled && isOpenRef.current) {
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
          // After assistant finishes speaking, restart listening if conversation is active
          if (conversationActive && !isListening) {
            setTimeout(() => {
              handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
            }, 500);
          }
        } else if (conversationActive && !isListening) {
          setTimeout(() => {
            handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
          }, 500);
        }
      }
    } else {
      console.log('[VoiceModal] Received non-assistant-message event:', event);
    }
  }, [voiceEnabled, conversationActive, isListening, startListening]);

  usePusher(userId || 0, handlePusherMessage);

  const handleStartConversation = () => {
    setConversationActive(true);
    stopSpeaking();
    handleVoiceInputRef.current && startListening(handleVoiceInputRef.current);
  };

  const handleStopConversation = () => {
    setConversationActive(false);
    stopListening();
    stopSpeaking();
  };

  const handleClose = () => {
    handleStopConversation();
    setMessages([]);
    onClose();
  };

  if (!isOpen) return null;

  // Calculate color based on audio level (green to red)
  const getAudioColor = () => {
    if (audioLevel < 20) return 'bg-status-error'; // Red - no sound
    if (audioLevel < 50) return 'bg-yellow-500'; // Yellow - low
    return 'bg-status-success'; // Green - good
  };

  // Calculate pulse size based on audio level
  const pulseSize = Math.max(1, audioLevel / 10);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-dark-charcoal/90 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl mx-4 bg-gradient-to-b from-dark-warm-gray to-dark-charcoal rounded-2xl shadow-2xl border border-primary-gold/20 p-6 md:p-8">
        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-text-medium hover:text-primary-gold transition-colors text-2xl"
        >
          ✕
        </button>

        {/* Robot Display */}
        <div className="text-center mb-6">
          <div className="relative inline-block">
            {/* Audio Level Indicator Rings */}
            {isListening && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div
                  className={`absolute rounded-full ${getAudioColor()} opacity-30 animate-ping`}
                  style={{
                    width: `${pulseSize * 20}px`,
                    height: `${pulseSize * 20}px`,
                  }}
                />
                <div
                  className={`absolute rounded-full ${getAudioColor()} opacity-20 animate-ping`}
                  style={{
                    width: `${pulseSize * 30}px`,
                    height: `${pulseSize * 30}px`,
                    animationDelay: '0.2s',
                  }}
                />
                <div
                  className={`absolute rounded-full ${getAudioColor()} opacity-10 animate-ping`}
                  style={{
                    width: `${pulseSize * 40}px`,
                    height: `${pulseSize * 40}px`,
                    animationDelay: '0.4s',
                  }}
                />
              </div>
            )}

            {/* Robot Emoji */}
            <div className="relative text-8xl md:text-9xl">
              {isListening ? (
                <div className="animate-bounce">
                  {(() => {
                    const brackets = '('.repeat(Math.floor(pulseSize));
                    const closingBrackets = ')'.repeat(Math.floor(pulseSize));
                    return `${brackets}🤖${closingBrackets}`;
                  })()}
                </div>
              ) : (
                '🤖'
              )}
            </div>
          </div>

          {/* Status Text */}
          <div className="mt-4">
            {error ? (
              <p className="text-status-error text-sm">{error}</p>
            ) : isListening ? (
              <div>
                <p className="text-primary-gold font-semibold text-lg mb-2">
                  {transcript || 'A ouvir...'}
                </p>
                <div className="flex items-center justify-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${getAudioColor()} animate-pulse`}></div>
                  <span className="text-text-medium text-sm">
                    Nível de áudio: {Math.round(audioLevel)}%
                  </span>
                </div>
              </div>
            ) : conversationActive ? (
              <p className="text-text-medium">Aguardando resposta...</p>
            ) : (
              <p className="text-text-medium">Carrega em "Falar" para começar</p>
            )}
          </div>
        </div>

        {/* Conversation History */}
        {messages.length > 0 && (
          <div className="max-h-64 overflow-y-auto space-y-3 mb-6 p-4 bg-dark-charcoal/50 rounded-lg border border-primary-gold/10">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary-gold text-dark-charcoal'
                      : 'bg-dark-warm-gray text-text-light'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-dark-warm-gray rounded-lg px-3 py-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-primary-gold rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-col gap-3">
          <div className="flex gap-3 justify-center">
            {!conversationActive ? (
              <button
                onClick={handleStartConversation}
                className="btn-primary px-8 py-4 text-lg flex items-center gap-2"
              >
                <span>🎤</span>
                Falar
              </button>
            ) : (
              <button
                onClick={handleStopConversation}
                className="bg-status-error hover:bg-status-error/80 text-white font-semibold px-8 py-4 rounded-lg transition-colors text-lg flex items-center gap-2"
              >
                <span>⏹️</span>
                Parar
              </button>
            )}
          </div>

          <div className="flex items-center justify-center gap-3 text-sm">
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
              🔊 {voiceEnabled ? 'Voz ON' : 'Voz OFF'}
            </button>
            <button
              onClick={() => {
                const text = messages.map(m => `${m.role}: ${m.content}`).join('\n');
                navigator.clipboard.writeText(text);
              }}
              className="btn-secondary text-sm"
              disabled={messages.length === 0}
            >
              📋 Copiar conversa
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceModal;


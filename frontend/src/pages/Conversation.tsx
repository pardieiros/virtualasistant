import { useState, useRef } from 'react';
import { useVoiceWebSocket } from '../hooks/useVoiceWebSocket';
import { AudioPlayer } from '../components/AudioPlayer';

/**
 * Conversation Page - Voice conversation mode with Jarvas
 * 
 * Features:
 * - Real-time voice conversation via WebSocket
 * - Live transcription display
 * - Audio playback of TTS responses
 * - Call-like UI with connection status
 */
export default function Conversation() {
  const [isActive, setIsActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [speakerMuted, setSpeakerMuted] = useState(false);
  const audioPlayerRef = useRef<any>(null);

  console.log('[Conversation] 🔄 Component render');

  const {
    connect,
    disconnect,
    status,
    transcript,
    llmResponse,
    error,
    isConnected,
    audioChunks,
  } = useVoiceWebSocket();

  console.log('[Conversation] 📊 Current state:', {
    isActive,
    isMuted,
    speakerMuted,
    status,
    isConnected,
    hasTranscript: !!transcript,
    hasLlmResponse: !!llmResponse,
    audioChunksCount: audioChunks.length,
    hasError: !!error
  });

  // Handle call start
  const handleStartCall = async () => {
    console.log('[Conversation] 📞 User clicked LIGAR button');
    try {
      console.log('[Conversation] 🚀 Calling connect()...');
      await connect();
      console.log('[Conversation] ✅ Connect successful, setting isActive=true');
      setIsActive(true);
    } catch (err) {
      console.error('[Conversation] ❌ Failed to start call:', err);
    }
  };

  // Handle call end
  const handleEndCall = () => {
    console.log('[Conversation] 📵 User clicked DESLIGAR button');
    disconnect();
    setIsActive(false);
    setIsMuted(false);
    console.log('[Conversation] ✅ Call ended, reset state');
  };

  // Get status display info
  const getStatusInfo = () => {
    let info;
    switch (status) {
      case 'connected':
        info = { text: 'Conectado', color: 'text-green-400' };
        break;
      case 'listening':
        info = { text: 'A Ouvir...', color: 'text-blue-400' };
        break;
      case 'thinking':
        info = { text: 'A Pensar...', color: 'text-yellow-400' };
        break;
      case 'speaking':
        info = { text: 'A Falar...', color: 'text-purple-400' };
        break;
      case 'error':
        info = { text: 'Erro', color: 'text-red-400' };
        break;
      case 'stopped':
        info = { text: 'Desconectado', color: 'text-gray-400' };
        break;
      default:
        info = { text: 'Aguardando...', color: 'text-gray-400' };
    }
    console.log('[Conversation] 🎨 Status display:', status, '→', info.text);
    return info;
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="h-full flex flex-col bg-dark-charcoal">
      {/* Header */}
      <div className="bg-muted-purple shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-primary-gold">
            Conversa Telefónica
          </h1>
          <p className="text-silver-gray text-sm mt-1">
            Fala continuamente com o Jarvas em tempo real
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Robot Animation */}
          <div className="flex justify-center mb-8">
            <div className="relative">
              <img
                src="/api/robot-gif/"
                alt="Jarvas Robot"
                className={`w-64 h-64 object-contain rounded-lg ${
                  status === 'speaking' ? 'animate-pulse' : ''
                }`}
              />
              {/* Status Indicator Overlay */}
              <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-70 rounded-b-lg py-2 px-4">
                <p className={`text-center font-semibold ${statusInfo.color}`}>
                  {statusInfo.text}
                </p>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 bg-red-900 bg-opacity-20 border border-red-500 rounded-lg p-4">
              <p className="text-red-400 text-sm">
                <span className="font-semibold">Erro:</span> {error}
              </p>
            </div>
          )}

          {/* Transcription Display */}
          {transcript && (
            <div className="mb-6 bg-muted-purple rounded-lg p-4 shadow-md">
              <h3 className="text-sm font-semibold text-primary-gold mb-2">
                Tu disseste:
              </h3>
              <p className="text-white">{transcript}</p>
            </div>
          )}

          {/* LLM Response Display */}
          {llmResponse && (
            <div className="mb-6 bg-soft-purple rounded-lg p-4 shadow-md">
              <h3 className="text-sm font-semibold text-primary-gold mb-2">
                Jarvas respondeu:
              </h3>
              <p className="text-white whitespace-pre-wrap">{llmResponse}</p>
            </div>
          )}

          {/* Control Buttons */}
          <div className="flex justify-center items-center gap-4 mb-8">
            {!isActive ? (
              <button
                onClick={handleStartCall}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-8 py-4 rounded-full shadow-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isConnected}
              >
                <span className="text-2xl">📞</span>
                <span className="font-semibold">Ligar</span>
              </button>
            ) : (
              <>
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`p-4 rounded-full shadow-lg transition-all transform hover:scale-105 ${
                    isMuted
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-muted-purple hover:bg-soft-purple'
                  }`}
                  title={isMuted ? 'Ativar Microfone' : 'Silenciar Microfone'}
                >
                  <span className="text-2xl">{isMuted ? '🔇' : '🎤'}</span>
                </button>

                <button
                  onClick={handleEndCall}
                  className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-8 py-4 rounded-full shadow-lg transition-all transform hover:scale-105"
                >
                  <span className="text-2xl">📵</span>
                  <span className="font-semibold">Desligar</span>
                </button>

                <button
                  onClick={() => setSpeakerMuted(!speakerMuted)}
                  className={`p-4 rounded-full shadow-lg transition-all transform hover:scale-105 ${
                    speakerMuted
                      ? 'bg-red-600 hover:bg-red-700'
                      : 'bg-muted-purple hover:bg-soft-purple'
                  }`}
                  title={speakerMuted ? 'Ativar Som' : 'Silenciar Som'}
                >
                  <span className="text-2xl">{speakerMuted ? '🔇' : '🔊'}</span>
                </button>
              </>
            )}
          </div>

          {/* Instructions */}
          {!isActive && (
            <div className="bg-muted-purple rounded-lg p-6 shadow-md">
              <h3 className="text-lg font-semibold text-primary-gold mb-3">
                Como Usar
              </h3>
              <ul className="space-y-2 text-silver-gray">
                <li className="flex items-start">
                  <span className="text-primary-gold mr-2">•</span>
                  <span>
                    Clica em <strong>"Ligar"</strong> para iniciar a conversa
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-gold mr-2">•</span>
                  <span>
                    Fala naturalmente - o Jarvas está sempre a ouvir
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-gold mr-2">•</span>
                  <span>
                    Vê a transcrição em tempo real no ecrã
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-gold mr-2">•</span>
                  <span>
                    O Jarvas responderá em voz e texto
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-primary-gold mr-2">•</span>
                  <span>
                    Usa os botões para silenciar o microfone ou o som
                  </span>
                </li>
              </ul>
            </div>
          )}

          {/* Connection Status */}
          {isActive && (
            <div className="text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-muted-purple rounded-full">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                  }`}
                />
                <span className="text-sm text-silver-gray">
                  {isConnected ? 'Conectado' : 'Desconectado'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Audio Player (hidden UI, handles playback) */}
      <AudioPlayer
        ref={audioPlayerRef}
        audioChunks={audioChunks}
        muted={speakerMuted}
      />
    </div>
  );
}


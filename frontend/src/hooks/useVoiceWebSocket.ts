import { useState, useRef, useCallback, useEffect } from 'react';
import { getToken } from '../utils/jwt';

/**
 * Voice WebSocket status type
 */
export type VoiceStatus = 
  | 'disconnected'
  | 'connected'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'error'
  | 'stopped';

/**
 * Audio chunk from TTS
 */
export interface AudioChunk {
  format: string;
  data: string; // base64 encoded audio
  timestamp: number;
}

/**
 * Custom hook for voice conversation via WebSocket
 * 
 * Features:
 * - WebSocket connection management
 * - Audio recording and streaming
 * - Real-time transcription
 * - LLM response streaming
 * - TTS audio chunks
 */
export function useVoiceWebSocket() {
  const [status, setStatus] = useState<VoiceStatus>('disconnected');
  const [transcript, setTranscript] = useState<string>('');
  const [llmResponse, setLlmResponse] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [audioChunks, setAudioChunks] = useState<AudioChunk[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const conversationIdRef = useRef<string>('');

  /**
   * Connect to WebSocket and start audio recording
   */
  const connect = useCallback(async () => {
    try {
      console.log('[VoiceWebSocket] 🎤 Requesting microphone permission...');
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 48000
        }
      });
      streamRef.current = stream;
      console.log('[VoiceWebSocket] ✅ Microphone permission granted', stream.getTracks());

      // Get auth token
      const token = getToken();
      console.log('[VoiceWebSocket] 🔑 Auth token:', token ? 'present' : 'MISSING');
      if (!token) {
        throw new Error('No authentication token');
      }

      // Determine WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/voice/?token=${token}`;
      console.log('[VoiceWebSocket] 🔌 Connecting to WebSocket:', wsUrl.replace(token, 'TOKEN_HIDDEN'));

      // Create WebSocket connection
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      console.log('[VoiceWebSocket] ⏳ WebSocket state:', ws.readyState, '(0=CONNECTING)');

      // WebSocket event handlers
      ws.onopen = () => {
        console.log('[VoiceWebSocket] ✅ WebSocket CONNECTED');
        setIsConnected(true);
        setError(null);

        // Send start message
        const conversationId = crypto.randomUUID();
        conversationIdRef.current = conversationId;
        
        const startMessage = {
          type: 'start',
          conversation_id: conversationId,
          lang: 'pt-PT'
        };
        console.log('[VoiceWebSocket] 📤 Sending START message:', startMessage);
        ws.send(JSON.stringify(startMessage));

        // Start audio recording
        console.log('[VoiceWebSocket] 🎙️ Starting audio recording...');
        startRecording(ws, stream);
      };

      ws.onmessage = (event) => {
        // Handle JSON messages
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            console.log('[VoiceWebSocket] 📥 Received message:', data.type, data);
            handleServerMessage(data);
          } catch (err) {
            console.error('[VoiceWebSocket] ❌ Failed to parse WebSocket message:', err);
          }
        } else {
          console.log('[VoiceWebSocket] 📥 Received binary data:', event.data);
        }
      };

      ws.onerror = (err) => {
        console.error('[VoiceWebSocket] ❌ WebSocket ERROR:', err);
        setError('Erro de conexão WebSocket');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('[VoiceWebSocket] 🔌 WebSocket CLOSED', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        setIsConnected(false);
        setStatus('disconnected');
        
        // Stop recording
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
        
        // Stop media stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };

    } catch (err: any) {
      console.error('[VoiceWebSocket] ❌ Failed to connect:', err);
      console.error('[VoiceWebSocket] Error details:', err.message, err.stack);
      setError(err.message || 'Failed to start conversation');
      setIsConnected(false);
      
      // Clean up stream if it was created
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    }
  }, []);

  /**
   * Disconnect WebSocket and stop recording
   */
  const disconnect = useCallback(() => {
    console.log('[VoiceWebSocket] 🛑 Disconnecting...');
    // Send stop message
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[VoiceWebSocket] 📤 Sending STOP message');
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
      wsRef.current.close();
    }
    wsRef.current = null;

    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    setIsConnected(false);
    setStatus('disconnected');
  }, []);

  /**
   * Start audio recording and streaming
   */
  const startRecording = (ws: WebSocket, stream: MediaStream) => {
    try {
      console.log('[VoiceWebSocket] 🎙️ Initializing MediaRecorder...');
      // Create MediaRecorder with Opus codec
      const options = { mimeType: 'audio/webm;codecs=opus' };
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      console.log('[VoiceWebSocket] 📊 MediaRecorder created:', {
        mimeType: mediaRecorder.mimeType,
        state: mediaRecorder.state
      });

      // Send audio chunks as they become available
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          console.log('[VoiceWebSocket] 🎵 Sending audio chunk:', event.data.size, 'bytes');
          // Send binary audio data
          ws.send(event.data);
        } else {
          console.warn('[VoiceWebSocket] ⚠️ Cannot send audio - size:', event.data.size, 'wsState:', ws.readyState);
        }
      };

      mediaRecorder.onstart = () => {
        console.log('[VoiceWebSocket] ▶️ MediaRecorder STARTED');
      };

      mediaRecorder.onstop = () => {
        console.log('[VoiceWebSocket] ⏹️ MediaRecorder STOPPED');
      };

      mediaRecorder.onerror = (err) => {
        console.error('[VoiceWebSocket] ❌ MediaRecorder ERROR:', err);
      };

      // Start recording with timeslice for low latency
      // Send chunks every 500ms
      mediaRecorder.start(500);
      
      console.log('[VoiceWebSocket] ✅ Audio recording started (500ms chunks)');
    } catch (err) {
      console.error('[VoiceWebSocket] ❌ Failed to start recording:', err);
      setError('Failed to start audio recording');
    }
  };

  /**
   * Handle server messages
   */
  const handleServerMessage = (data: any) => {
    const { type } = data;

    switch (type) {
      case 'status':
        console.log('[VoiceWebSocket] 📊 Status changed:', data.value);
        setStatus(data.value as VoiceStatus);
        break;

      case 'partial_transcript':
        console.log('[VoiceWebSocket] 📝 Partial transcript:', data.text);
        setTranscript(data.text);
        break;

      case 'final_transcript':
        console.log('[VoiceWebSocket] ✅ Final transcript:', data.text);
        setTranscript(data.text);
        break;

      case 'llm_text_delta':
        console.log('[VoiceWebSocket] 💬 LLM delta:', data.text);
        setLlmResponse(prev => prev + data.text);
        break;

      case 'llm_text_final':
        console.log('[VoiceWebSocket] ✅ LLM final:', data.text);
        setLlmResponse(data.text);
        break;

      case 'tts_audio_chunk':
        console.log('[VoiceWebSocket] 🔊 TTS audio chunk received:', data.format, data.data_b64?.length, 'chars');
        // Add audio chunk to queue
        const chunk: AudioChunk = {
          format: data.format,
          data: data.data_b64,
          timestamp: Date.now()
        };
        setAudioChunks(prev => [...prev, chunk]);
        break;

      case 'error':
        console.error('[VoiceWebSocket] ❌ Server error:', data.message);
        setError(data.message);
        setStatus('error');
        break;

      case 'pong':
        console.log('[VoiceWebSocket] 🏓 Pong received');
        // Heartbeat response
        break;

      default:
        console.warn('[VoiceWebSocket] ⚠️ Unknown message type:', type);
    }
  };

  /**
   * Send ping to keep connection alive
   */
  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  /**
   * Heartbeat ping every 30 seconds
   */
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(sendPing, 30000);
    return () => clearInterval(interval);
  }, [isConnected, sendPing]);

  /**
   * Clear audio chunks after they've been played
   */
  const clearAudioChunks = useCallback(() => {
    setAudioChunks([]);
  }, []);

  return {
    connect,
    disconnect,
    status,
    transcript,
    llmResponse,
    error,
    isConnected,
    audioChunks,
    clearAudioChunks,
  };
}


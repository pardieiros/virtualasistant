import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { AudioChunk } from '../hooks/useVoiceWebSocket';

interface AudioPlayerProps {
  audioChunks: AudioChunk[];
  muted?: boolean;
}

/**
 * AudioPlayer component
 * 
 * Handles playback of TTS audio chunks in sequence.
 * Manages a queue of audio chunks and plays them without gaps.
 */
export const AudioPlayer = forwardRef<any, AudioPlayerProps>(
  ({ audioChunks, muted = false }, ref) => {
    const audioContextRef = useRef<AudioContext | null>(null);
    const audioQueueRef = useRef<AudioChunk[]>([]);
    const isPlayingRef = useRef(false);
    const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
    const nextPlayTimeRef = useRef(0);
    const gainNodeRef = useRef<GainNode | null>(null);

  /**
   * Initialize Audio Context
   */
  useEffect(() => {
    if (!audioContextRef.current) {
      console.log('[AudioPlayer] 🎵 Initializing AudioContext...');
      audioContextRef.current = new AudioContext();
      console.log('[AudioPlayer] ℹ️ AudioContext state:', audioContextRef.current.state);
      console.log('[AudioPlayer] ℹ️ Sample rate:', audioContextRef.current.sampleRate);
      
      // Create gain node for volume control
      gainNodeRef.current = audioContextRef.current.createGain();
      gainNodeRef.current.connect(audioContextRef.current.destination);
      console.log('[AudioPlayer] ✅ AudioContext initialized');
    }

      return () => {
        // Cleanup on unmount
        if (currentSourceRef.current) {
          try {
            currentSourceRef.current.stop();
          } catch (e) {
            // Ignore if already stopped
          }
        }
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close();
        }
      };
    }, []);

  /**
   * Handle mute/unmute
   */
  useEffect(() => {
    if (gainNodeRef.current) {
      const newGain = muted ? 0 : 1;
      console.log('[AudioPlayer] 🔊 Setting gain:', newGain, '(muted:', muted, ')');
      gainNodeRef.current.gain.value = newGain;
    }
  }, [muted]);

  /**
   * Process new audio chunks
   */
  useEffect(() => {
    if (audioChunks.length === 0) return;

    console.log('[AudioPlayer] 📦 Received audioChunks:', audioChunks.length, 'total');

    // Add new chunks to queue
    const newChunks = audioChunks.filter(
      chunk => !audioQueueRef.current.some(q => q.timestamp === chunk.timestamp)
    );

    if (newChunks.length > 0) {
      console.log('[AudioPlayer] ➕ Adding', newChunks.length, 'new chunks to queue');
      audioQueueRef.current.push(...newChunks);
      console.log('[AudioPlayer] 📊 Queue size:', audioQueueRef.current.length);
      
      // Start playing if not already playing
      if (!isPlayingRef.current) {
        console.log('[AudioPlayer] ▶️ Starting playback...');
        playNextChunk();
      } else {
        console.log('[AudioPlayer] ⏯️ Already playing, chunks queued');
      }
    }
  }, [audioChunks]);

  /**
   * Play next chunk in queue
   */
  const playNextChunk = async () => {
    if (audioQueueRef.current.length === 0) {
      console.log('[AudioPlayer] ✅ Queue empty, stopping playback');
      isPlayingRef.current = false;
      return;
    }

    if (!audioContextRef.current || !gainNodeRef.current) {
      console.error('[AudioPlayer] ❌ Audio context not initialized');
      return;
    }

    isPlayingRef.current = true;

    try {
      const chunk = audioQueueRef.current.shift();
      if (!chunk) {
        console.warn('[AudioPlayer] ⚠️ No chunk to play');
        return;
      }

      console.log('[AudioPlayer] 🎵 Playing chunk:', {
        format: chunk.format,
        dataLength: chunk.data.length,
        timestamp: chunk.timestamp,
        remainingInQueue: audioQueueRef.current.length
      });

      // Decode base64 to array buffer
      const binaryString = atob(chunk.data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      console.log('[AudioPlayer] 📊 Decoded binary data:', bytes.length, 'bytes');

      // Decode audio data
      console.log('[AudioPlayer] 🔄 Decoding audio data...');
      const audioBuffer = await audioContextRef.current.decodeAudioData(
        bytes.buffer
      );
      console.log('[AudioPlayer] ✅ Audio decoded:', {
        duration: audioBuffer.duration,
        channels: audioBuffer.numberOfChannels,
        sampleRate: audioBuffer.sampleRate,
        length: audioBuffer.length
      });

      // Create source node
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(gainNodeRef.current);
      currentSourceRef.current = source;

      // Calculate start time
      const currentTime = audioContextRef.current.currentTime;
      const startTime = Math.max(currentTime, nextPlayTimeRef.current);
      console.log('[AudioPlayer] ⏰ Scheduling playback:', {
        currentTime,
        startTime,
        nextPlayTime: nextPlayTimeRef.current,
        duration: audioBuffer.duration
      });
      
      // Play
      source.start(startTime);
      console.log('[AudioPlayer] ▶️ Started playing at', startTime);

      // Update next play time
      nextPlayTimeRef.current = startTime + audioBuffer.duration;

      // When this chunk ends, play next
      source.onended = () => {
        console.log('[AudioPlayer] ✅ Chunk finished playing');
        currentSourceRef.current = null;
        playNextChunk();
      };

    } catch (error) {
      console.error('[AudioPlayer] ❌ Error playing audio chunk:', error);
      isPlayingRef.current = false;
      
      // Try next chunk if available
      if (audioQueueRef.current.length > 0) {
        console.log('[AudioPlayer] 🔄 Trying next chunk after error...');
        playNextChunk();
      }
    }
  };

  /**
   * Stop playback
   */
  const stop = () => {
    console.log('[AudioPlayer] ⏹️ Stopping playback');
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
        console.log('[AudioPlayer] ✅ Current source stopped');
      } catch (e) {
        console.warn('[AudioPlayer] ⚠️ Error stopping source (may already be stopped):', e);
      }
      currentSourceRef.current = null;
    }
    
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    nextPlayTimeRef.current = 0;
    console.log('[AudioPlayer] ✅ Playback stopped, queue cleared');
  };

  /**
   * Clear queue
   */
  const clearQueue = () => {
    console.log('[AudioPlayer] 🗑️ Clearing queue (had', audioQueueRef.current.length, 'chunks)');
    audioQueueRef.current = [];
  };

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      stop,
      clearQueue,
    }));

    // This component doesn't render anything
    return null;
  }
);

AudioPlayer.displayName = 'AudioPlayer';


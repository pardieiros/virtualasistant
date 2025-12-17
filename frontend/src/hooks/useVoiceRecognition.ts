import { useState, useRef, useEffect } from 'react';

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: Event) => void;
  onend: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

export const useVoiceRecognition = () => {
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0); // 0-100
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const onFinalTranscriptRef = useRef<((text: string) => void) | null>(null);
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalTranscriptRef = useRef<string>('');
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastSpeechTimeRef = useRef<number>(0);
  const lastValidTranscriptTimeRef = useRef<number>(0);
  const consecutiveNoiseCountRef = useRef<number>(0);
  const currentInterimTranscriptRef = useRef<string>('');
  const isSendingRef = useRef<boolean>(false); // Flag to prevent duplicate sends
  
  // Noise suppression constants
  const MIN_AUDIO_LEVEL_FOR_SPEECH = 15; // Minimum audio level to consider as speech (for display only)
  const MIN_TRANSCRIPT_LENGTH = 1; // Minimum number of characters to consider valid (very permissive)
  const MAX_CONSECUTIVE_NOISE = 10; // Max consecutive noise detections before ignoring (more permissive)

  // Audio level detection
  const startAudioLevelDetection = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateAudioLevel = () => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const level = Math.min(100, (average / 255) * 100);
        setAudioLevel(level);

        // Update last speech time if audio level is detected (for display purposes)
        // Note: We rely on Speech Recognition API for actual speech detection, not audio level
        if (level > MIN_AUDIO_LEVEL_FOR_SPEECH) {
          lastSpeechTimeRef.current = Date.now();
        }

        animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
      };

      updateAudioLevel();
    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopAudioLevelDetection = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  };

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'pt-PT';

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimTranscript = '';
      let newFinalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        const isFinal = event.results[i].isFinal;
        if (isFinal) {
          newFinalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      // Noise suppression: validate transcript before processing
      // Very permissive validation - we trust the Speech Recognition API
      const isValidTranscript = (text: string): boolean => {
        const trimmed = text.trim();
        
        // Basic checks only
        if (!trimmed || trimmed.length < MIN_TRANSCRIPT_LENGTH) {
          return false;
        }
        
        // Check for obviously invalid patterns (only very obvious noise)
        // Reject if it's just a single repeated character (like "aaaa" or "....")
        if (trimmed.length > 3) {
          const uniqueChars = new Set(trimmed.toLowerCase().replace(/\s/g, '')).size;
          if (uniqueChars === 1) {
            return false;
          }
        }
        
        return true;
      };

      // Process final transcripts
      if (newFinalTranscript) {
        const updatedFinal = finalTranscriptRef.current + newFinalTranscript;
        finalTranscriptRef.current = updatedFinal;
        setTranscript(updatedFinal + interimTranscript);
        lastSpeechTimeRef.current = Date.now();
        
        // Validate the complete accumulated transcript
        const completeText = updatedFinal.trim();
        const isCompleteValid = isValidTranscript(completeText);
        
        if (isCompleteValid) {
          lastValidTranscriptTimeRef.current = Date.now();
          consecutiveNoiseCountRef.current = 0; // Reset noise counter on valid transcript
          
          // Clear any existing timeout
          if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current);
          }
          
          // For final results, send after a shorter delay (1 second) to allow for more final results
          silenceTimeoutRef.current = setTimeout(() => {
            if (!isSendingRef.current) {
              const timeSinceLastSpeech = Date.now() - lastSpeechTimeRef.current;
              const finalText = finalTranscriptRef.current.trim();
              
              if (
                timeSinceLastSpeech >= 1000 &&
                onFinalTranscriptRef.current && 
                finalText &&
                isValidTranscript(finalText)
              ) {
                isSendingRef.current = true;
                onFinalTranscriptRef.current(finalText);
                finalTranscriptRef.current = '';
                currentInterimTranscriptRef.current = '';
                setTranscript('');
                // Reset flag after a short delay
                setTimeout(() => {
                  isSendingRef.current = false;
                }, 500);
              }
            }
          }, 1000);
        } else {
          // Invalid transcript (likely noise) - increment counter
          consecutiveNoiseCountRef.current += 1;
        }
      } else if (interimTranscript) {
        // Update display with interim transcript
        currentInterimTranscriptRef.current = interimTranscript;
        setTranscript(finalTranscriptRef.current + interimTranscript);
        lastSpeechTimeRef.current = Date.now();
        
        // Clear any existing timeout
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
        }
        
        // For interim results, wait longer (2 seconds) before sending
        silenceTimeoutRef.current = setTimeout(() => {
          if (!isSendingRef.current) {
          const timeSinceLastSpeech = Date.now() - lastSpeechTimeRef.current;
            // Get the current transcript (final + interim if available)
            const finalText = (finalTranscriptRef.current + currentInterimTranscriptRef.current).trim();
            
            // Only send if:
            // 1. We haven't heard speech in the last 2 seconds
            // 2. We have text
            // 3. The transcript passes validation
            if (
              timeSinceLastSpeech >= 2000 &&
              onFinalTranscriptRef.current && 
              finalText &&
              isValidTranscript(finalText)
            ) {
              isSendingRef.current = true;
              onFinalTranscriptRef.current(finalText);
              finalTranscriptRef.current = '';
              currentInterimTranscriptRef.current = '';
              setTranscript('');
              // Reset flag after a short delay
              setTimeout(() => {
                isSendingRef.current = false;
              }, 500);
            } else if (finalText && !isValidTranscript(finalText)) {
              // If validation failed, clear the transcript
              finalTranscriptRef.current = '';
              currentInterimTranscriptRef.current = '';
              setTranscript('');
              consecutiveNoiseCountRef.current = 0;
            } else if (consecutiveNoiseCountRef.current >= MAX_CONSECUTIVE_NOISE) {
              // Too many noise detections, clear everything
            finalTranscriptRef.current = '';
              currentInterimTranscriptRef.current = '';
            setTranscript('');
              consecutiveNoiseCountRef.current = 0;
            }
          }
        }, 2000);
      }
    };

    recognition.onerror = (event: any) => {
      setError(`Speech recognition error: ${event.error}`);
      setIsListening(false);
      stopAudioLevelDetection();
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      stopAudioLevelDetection();
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      
      // Auto-restart if we're still supposed to be listening
      if (onFinalTranscriptRef.current) {
        setTimeout(() => {
          if (recognitionRef.current && onFinalTranscriptRef.current) {
            try {
              recognitionRef.current.start();
              setIsListening(true);
              startAudioLevelDetection();
            } catch (err) {
              console.error('Error restarting recognition:', err);
            }
          }
        }, 100);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      stopAudioLevelDetection();
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
    };
  }, []);

  const startListening = (onFinalTranscript?: (text: string) => void) => {
    if (recognitionRef.current && !isListening) {
      setTranscript('');
      finalTranscriptRef.current = '';
      currentInterimTranscriptRef.current = '';
      setError(null);
      lastSpeechTimeRef.current = Date.now();
      lastValidTranscriptTimeRef.current = Date.now();
      consecutiveNoiseCountRef.current = 0;
      isSendingRef.current = false;
      setIsListening(true);
      onFinalTranscriptRef.current = onFinalTranscript || null;
      recognitionRef.current.start();
      startAudioLevelDetection();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
      stopAudioLevelDetection();
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      onFinalTranscriptRef.current = null;
    }
  };

  return {
    transcript,
    isListening,
    error,
    audioLevel,
    startListening,
    stopListening,
  };
};


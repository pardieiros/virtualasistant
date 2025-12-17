import { ttsAPI } from '../api/client';

// Keep track of current audio element for backend TTS
let currentAudio: HTMLAudioElement | null = null;

// Wait for voices to be loaded (they load asynchronously)
const waitForVoices = (): Promise<SpeechSynthesisVoice[]> => {
  return new Promise((resolve) => {
  const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      resolve(voices);
      return;
    }

    // Voices load asynchronously, wait for the voiceschanged event
    const onVoicesChanged = () => {
      const loadedVoices = window.speechSynthesis.getVoices();
      if (loadedVoices.length > 0) {
        window.speechSynthesis.removeEventListener('voiceschanged', onVoicesChanged);
        resolve(loadedVoices);
      }
    };

    window.speechSynthesis.addEventListener('voiceschanged', onVoicesChanged);
    
    // Fallback timeout - use whatever is available after 1 second
    setTimeout(() => {
      window.speechSynthesis.removeEventListener('voiceschanged', onVoicesChanged);
      const availableVoices = window.speechSynthesis.getVoices();
      resolve(availableVoices);
    }, 1000);
  });
};

const getPortugueseVoice = async (): Promise<SpeechSynthesisVoice | null> => {
  const voices = await waitForVoices();
  
  if (voices.length === 0) {
    return null;
  }
  
  // First try to find pt-PT specifically
  const ptPTVoice = voices.find(
    (voice) => voice.lang === 'pt-PT' || voice.lang.startsWith('pt-PT')
  );
  
  if (ptPTVoice) return ptPTVoice;
  
  // Fallback: look for Portuguese voice with Portugal in the name
  const portugalVoice = voices.find(
    (voice) => voice.lang === 'pt' && voice.name.toLowerCase().includes('portugal')
  );
  
  if (portugalVoice) return portugalVoice;
  
  // Last fallback: any Portuguese voice
  const anyPortugueseVoice = voices.find((voice) => voice.lang === 'pt' || voice.lang.startsWith('pt-'));
  if (anyPortugueseVoice) return anyPortugueseVoice;
  
  // If no Portuguese voice, use default voice (usually the first one)
  return voices[0] || null;
};

/**
 * Speak text using backend TTS service (preferred) or Web Speech API (fallback)
 */
const speakFromBackend = async (text: string): Promise<void> => {
  return new Promise(async (resolve) => {
    try {
      // Stop any ongoing audio first
      stopSpeaking();
      
      const audioBlob = await ttsAPI.generate(text);
      
      // Validate blob
      if (!audioBlob || audioBlob.size === 0) {
        throw new Error('Received empty audio blob from TTS service');
      }
      
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      // Set volume and preload
      audio.volume = 1.0;
      audio.preload = 'auto';
      
      // Store reference to current audio for stopping
      currentAudio = audio;
      
      // Wait for audio to be ready
      audio.addEventListener('loadeddata', () => {
        audio.play().then(() => {
          // Success - audio is playing, will resolve on onended
        }).catch((error) => {
          console.warn('Autoplay blocked, falling back to Web Speech API:', error);
          // Autoplay was blocked - reject to allow fallback
          URL.revokeObjectURL(audioUrl);
          currentAudio = null;
          // Fallback to Web Speech API
          speakWithWebSpeech(text).then(resolve).catch(() => resolve());
        });
      }, { once: true });
      
      // Add timeout for audio loading
      const loadTimeout = setTimeout(() => {
        if (currentAudio === audio && audio.readyState < 2) {
          console.error('Audio loading timeout');
          audio.onerror?.(new Event('timeout'));
        }
      }, 10000);
      
      audio.addEventListener('loadeddata', () => {
        clearTimeout(loadTimeout);
      }, { once: true });
      
      audio.addEventListener('error', () => {
        clearTimeout(loadTimeout);
      }, { once: true });
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        resolve();
      };
      
      audio.onerror = (e) => {
        const errorMsg = audio.error ? `Error code: ${audio.error.code}, message: ${audio.error.message}` : 'Unknown error';
        console.error('Error playing backend TTS audio:', errorMsg, e);
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        // Fallback to Web Speech API
        speakWithWebSpeech(text).then(resolve).catch(() => resolve());
      };
      
      // Load the audio with error handling
      try {
        audio.load();
      } catch (loadError) {
        console.error('Error loading audio element:', loadError);
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        speakWithWebSpeech(text).then(resolve).catch(() => resolve());
        return;
      }
      
    } catch (error: any) {
      console.error('Error generating speech from backend:', error);
      // Fallback to Web Speech API
      speakWithWebSpeech(text).then(resolve).catch(() => resolve());
    }
  });
};

/**
 * Speak text using Web Speech API (browser built-in)
 */
const speakWithWebSpeech = async (text: string): Promise<void> => {
  return new Promise(async (resolve) => {
    if (!('speechSynthesis' in window)) {
      resolve();
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'pt-PT';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Try to find and set Portuguese (Portugal) voice
    const voice = await getPortugueseVoice();
    if (voice) {
      utterance.voice = voice;
    }

    utterance.onend = () => {
      resolve();
    };

    utterance.onerror = () => {
      resolve();
    };

    try {
    window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error('Error starting speech synthesis:', error);
      resolve();
    }
  });
};

export const speak = async (text: string, enabled: boolean = true): Promise<void> => {
  if (!enabled) {
    return;
  }

  // Try backend TTS first (better quality, always works)
  try {
    await speakFromBackend(text);
  } catch (error) {
    // Fallback to Web Speech API if backend fails
    console.warn('Backend TTS failed, falling back to Web Speech API');
    await speakWithWebSpeech(text);
  }
};

/**
 * Play audio from base64 string (received from Pusher)
 */
export const playAudioFromBase64 = async (audioBase64: string, format: string = 'wav'): Promise<void> => {
  return new Promise((resolve, reject) => {
    try {
      // Stop any ongoing audio first
      stopSpeaking();
      
      // Convert base64 to blob
      const byteCharacters = atob(audioBase64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: `audio/${format}` });
      
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      
      // Set volume and preload
      audio.volume = 1.0;
      audio.preload = 'auto';
      
      // Store reference to current audio for stopping
      currentAudio = audio;
      
      // Wait for audio to be ready
      audio.addEventListener('loadeddata', () => {
        // Try to play - if it fails due to autoplay policy, reject to trigger fallback
        audio.play().then(() => {
          // Success - audio is playing, will resolve on onended
        }).catch((error) => {
          console.warn('Autoplay blocked:', error);
          // Autoplay was blocked - reject to allow caller to fallback to TTS
          URL.revokeObjectURL(audioUrl);
          currentAudio = null;
          reject(error);
        });
      }, { once: true });
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        resolve();
      };
      
      audio.onerror = (e) => {
        console.error('Error playing audio from base64:', e);
        URL.revokeObjectURL(audioUrl);
        currentAudio = null;
        resolve(); // Resolve instead of reject to allow fallback
      };
      
      // Load the audio
      audio.load();
      
    } catch (error) {
      console.error('Error setting up audio from base64:', error);
      resolve(); // Resolve instead of reject to allow fallback
    }
  });
};

export const stopSpeaking = (): void => {
  // Stop backend TTS audio if playing
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  
  // Stop Web Speech API if active
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
};

// Utility function to check available voices (for debugging)
export const getAvailableVoices = async (): Promise<SpeechSynthesisVoice[]> => {
  return await waitForVoices();
};

// Check if speech synthesis is supported
export const isSpeechSynthesisSupported = (): boolean => {
  return 'speechSynthesis' in window;
};


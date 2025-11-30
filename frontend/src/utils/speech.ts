const getPortugueseVoice = (): SpeechSynthesisVoice | null => {
  const voices = window.speechSynthesis.getVoices();
  
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
  return voices.find((voice) => voice.lang === 'pt') || null;
};

export const speak = (text: string, enabled: boolean = true): Promise<void> => {
  return new Promise((resolve) => {
    if (!enabled || !('speechSynthesis' in window)) {
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
    const ptPTVoice = getPortugueseVoice();
    if (ptPTVoice) {
      utterance.voice = ptPTVoice;
    }

    utterance.onend = () => {
      resolve();
    };

    utterance.onerror = () => {
      resolve();
    };

    window.speechSynthesis.speak(utterance);
  });
};

export const stopSpeaking = (): void => {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
};


# Configuração de Vozes TTS (Text-to-Speech)

## Problema

A Web Speech API depende das vozes instaladas no sistema operativo. Em PWAs, especialmente em dispositivos móveis, pode não haver vozes disponíveis ou podem não estar carregadas.

## Soluções

### 1. Instalar Vozes no Sistema (Desktop)

#### Windows
1. Abrir **Configurações** → **Hora e idioma** → **Fala**
2. Adicionar português (Portugal) se disponível
3. Instalar pacotes de voz adicionais se necessário

#### macOS
1. Abrir **Preferências do Sistema** → **Acessibilidade** → **Fala**
2. Clicar em **Sistema de Vozes**
3. Adicionar português (Portugal) se disponível

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install speech-dispatcher espeak-ng espeak-ng-pt

# Ou usar festival
sudo apt-get install festival festvox-pt
```

### 2. Verificar Vozes Disponíveis no Browser

O código agora aguarda automaticamente que as vozes sejam carregadas. Para verificar quais vozes estão disponíveis:

1. Abrir a consola do browser (F12)
2. Executar:
```javascript
speechSynthesis.getVoices().forEach(voice => {
  console.log(voice.name, voice.lang);
});
```

### 3. Solução Backend-Based (Recomendado para Produção)

Para uma solução mais robusta, considera usar um serviço de TTS no backend:

#### Opções:
- **Google Cloud Text-to-Speech** (pago, mas muito bom)
- **Azure Cognitive Services Speech** (pago)
- **ElevenLabs** (pago, vozes muito naturais)
- **Coqui TTS** (open source, pode correr localmente)
- **Piper TTS** (open source, leve e rápido)

#### Exemplo de implementação com backend:

```python
# backend/assistant/services/tts_service.py
from gtts import gTTS
import io

def generate_speech(text: str, lang: str = 'pt') -> bytes:
    """Generate speech audio from text"""
    tts = gTTS(text=text, lang=lang, slow=False)
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    return audio_buffer.read()
```

E no frontend, reproduzir o áudio:

```typescript
// frontend/src/utils/speech.ts
export const speakFromBackend = async (text: string): Promise<void> => {
  const response = await fetch('/api/tts/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, lang: 'pt-PT' })
  });
  
  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  
  return new Promise((resolve) => {
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      resolve();
    };
    audio.play();
  });
};
```

### 4. Solução Híbrida (Recomendado)

O código atual já tem fallbacks:
1. Tenta usar Web Speech API (se vozes disponíveis)
2. Se não houver vozes, mostra aviso mas não quebra
3. Podes adicionar fallback para backend TTS

## Melhorias Implementadas

✅ Aguarda que as vozes sejam carregadas (carregamento assíncrono)
✅ Fallback para qualquer voz disponível se não houver português
✅ Tratamento de erros melhorado
✅ Timeout de segurança (1 segundo)

## Próximos Passos

Se quiseres implementar TTS no backend:
1. Escolher um serviço de TTS
2. Criar endpoint `/api/tts/` no backend
3. Modificar `speak()` para tentar backend primeiro, depois Web Speech API
4. Cachear áudio gerado para melhor performance


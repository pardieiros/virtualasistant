# TTS API Documentation

## Overview

This document describes how the Personal Assistant backend communicates with the TTS (Text-to-Speech) service. The TTS service is expected to be a separate API that converts text to audio.

## Backend Configuration

The TTS service URL is configured in Django settings:

```python
TTS_SERVICE_URL = 'http://192.168.1.73:8010/api/tts/'
```

You can configure this via environment variable:
```bash
TTS_SERVICE_URL=http://your-tts-server:8010/api/tts/
```

---

## API Request (Backend → TTS Service)

### Endpoint
```
POST /api/tts/
```

### Request Headers
```
Content-Type: application/json
```

### Request Body (JSON)
```json
{
  "text": "Olá! Como posso ajudar?"
}
```

### Request Parameters

| Parameter | Type   | Required | Description                           |
|-----------|--------|----------|---------------------------------------|
| `text`    | string | Yes      | The text to convert to speech        |

### Example Request (curl)
```bash
curl -X POST http://localhost:8010/api/tts/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá! Como posso ajudar?"}'
```

### Example Request (Python)
```python
import requests

response = requests.post(
    'http://localhost:8010/api/tts/',
    json={'text': 'Olá! Como posso ajudar?'},
    headers={'Content-Type': 'application/json'},
    timeout=10
)

if response.status_code == 200:
    audio_data = response.content  # Binary WAV data
    with open('output.wav', 'wb') as f:
        f.write(audio_data)
```

---

## API Response (TTS Service → Backend)

### Success Response

**Status Code:** `200 OK`

**Content-Type:** `audio/wav` or `application/octet-stream`

**Body:** Binary audio data in WAV format

### Response Format

The TTS service must return:
- **Raw audio bytes** in WAV format
- **NOT** JSON with base64 encoded audio
- **NOT** any other audio format (MP3, OGG, etc.)

### WAV Format Specifications

Recommended WAV format:
- **Sample Rate:** 22050 Hz (or 16000 Hz)
- **Channels:** Mono (1 channel)
- **Bit Depth:** 16-bit PCM
- **Format:** PCM WAV

### Error Response

**Status Code:** `400`, `500`, or `503`

**Content-Type:** `application/json`

**Body:**
```json
{
  "error": "Error message description"
}
```

---

## Backend Processing

### How the Backend Uses TTS

1. **Request Generation**
   ```python
   from assistant.services.tts_service import generate_speech
   
   audio_data = generate_speech("Hello, world!")
   # Returns: bytes (WAV format) or None if error
   ```

2. **Audio Encoding for Frontend**
   ```python
   import base64
   
   if audio_data:
       audio_base64 = base64.b64encode(audio_data).decode('utf-8')
       # Send to frontend via Pusher/HTTP
   ```

3. **Timeout Configuration**
   - Default timeout: 10 seconds
   - If TTS takes longer, request will fail
   - Backend will continue without audio

---

## Example TTS API Implementation

### Using Piper TTS (Python)

```python
from flask import Flask, request, send_file, jsonify
from piper import PiperVoice
import io
import wave

app = Flask(__name__)

# Load Piper voice model
voice = PiperVoice.load('path/to/model.onnx')

@app.route('/api/tts/', methods=['POST'])
def text_to_speech():
    try:
        # Get text from request
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate audio using Piper
        audio_bytes = io.BytesIO()
        
        with wave.open(audio_bytes, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(22050)  # Sample rate
            
            # Generate audio from text
            for audio_chunk in voice.synthesize_stream_raw(text):
                wav_file.writeframes(audio_chunk)
        
        # Return WAV file
        audio_bytes.seek(0)
        return send_file(
            audio_bytes,
            mimetype='audio/wav',
            as_attachment=False,
            download_name='speech.wav'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8010)
```

### Using gTTS (Python - Alternative)

```python
from flask import Flask, request, send_file, jsonify
from gtts import gTTS
import io

app = Flask(__name__)

@app.route('/api/tts/', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate speech using gTTS
        tts = gTTS(text=text, lang='pt')  # Portuguese
        
        # Save to BytesIO
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        
        # Note: gTTS returns MP3, you may need to convert to WAV
        return send_file(
            audio_bytes,
            mimetype='audio/wav',
            as_attachment=False
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8010)
```

### Using FastAPI (Modern Alternative)

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from piper import PiperVoice
import io
import wave

app = FastAPI()

# Load voice model
voice = PiperVoice.load('path/to/model.onnx')

class TTSRequest(BaseModel):
    text: str

@app.post("/api/tts/")
async def text_to_speech(request: TTSRequest):
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Generate audio
        audio_bytes = io.BytesIO()
        
        with wave.open(audio_bytes, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            
            for audio_chunk in voice.synthesize_stream_raw(request.text):
                wav_file.writeframes(audio_chunk)
        
        audio_bytes.seek(0)
        
        return StreamingResponse(
            audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

---

## Testing the TTS API

### 1. Test with curl
```bash
# Send request and save audio
curl -X POST http://192.168.1.73:8010/api/tts/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá, isto é um teste"}' \
  --output test.wav

# Play the audio (Linux)
aplay test.wav

# Play the audio (macOS)
afplay test.wav
```

### 2. Test with Python
```python
import requests

response = requests.post(
    'http://192.168.1.73:8010/api/tts/',
    json={'text': 'Olá, isto é um teste'},
    timeout=10
)

print(f"Status: {response.status_code}")
print(f"Size: {len(response.content)} bytes")

if response.status_code == 200:
    with open('test.wav', 'wb') as f:
        f.write(response.content)
    print("Audio saved to test.wav")
```

### 3. Test with the Backend
```python
# Django shell
python manage.py shell

from assistant.services.tts_service import generate_speech

audio = generate_speech("Olá, mundo!")
if audio:
    with open('test.wav', 'wb') as f:
        f.write(audio)
    print(f"Audio generated: {len(audio)} bytes")
else:
    print("Failed to generate audio")
```

---

## Troubleshooting

### Common Issues

#### 1. Connection Refused (Errno 111)
```
Error calling TTS service: Failed to establish a new connection: [Errno 111] Connection refused
```

**Solutions:**
- Verify TTS service is running: `curl http://192.168.1.73:8010/api/tts/`
- Check firewall settings
- Verify the IP address and port are correct

#### 2. Timeout
```
Error calling TTS service: Timeout
```

**Solutions:**
- Increase timeout in `tts_service.py` (line 30)
- Optimize TTS service response time
- Use faster voice models

#### 3. Invalid Audio Format
```
Frontend can't play audio
```

**Solutions:**
- Ensure TTS returns WAV format (not MP3, OGG, etc.)
- Check WAV format: `file test.wav` should show "WAVE audio"
- Verify sample rate and bit depth

#### 4. Audio Quality Issues

**Solutions:**
- Increase sample rate (22050 Hz or 44100 Hz)
- Use higher quality voice models
- Check for audio clipping or distortion

---

## Performance Considerations

1. **Response Time**
   - Target: < 2 seconds for short text
   - Timeout: 10 seconds maximum

2. **Audio Size**
   - Typical: 50-200 KB for short responses
   - Pusher limit: ~10 KB (audio may be excluded if too large)

3. **Caching**
   - Consider caching common phrases
   - Use CDN for frequently used audio

4. **Load Balancing**
   - Multiple TTS instances for high traffic
   - Queue system for async processing

---

## Voice Models

### Piper Models (Recommended)

Download Portuguese voices from:
https://github.com/rhasspy/piper/releases

Recommended models:
- `pt_BR-faber-medium` (Brazilian Portuguese, good quality)
- `pt_PT-tugao-medium` (European Portuguese)

### Installation
```bash
# Download model
wget https://github.com/rhasspy/piper/releases/download/v1.0.0/pt_BR-faber-medium.tar.gz

# Extract
tar -xzf pt_BR-faber-medium.tar.gz

# Use in your TTS service
voice = PiperVoice.load('pt_BR-faber-medium.onnx')
```

---

## Security Considerations

1. **Input Validation**
   - Limit text length (e.g., 500 characters max)
   - Sanitize input to prevent injection attacks

2. **Rate Limiting**
   - Implement rate limiting per IP/user
   - Prevent abuse and DoS attacks

3. **Authentication** (Optional)
   - Add API key authentication if needed
   - Use HTTPS in production

---

## Docker Deployment Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Piper TTS
RUN pip install piper-tts flask

# Copy voice models
COPY models/ /app/models/

# Copy API code
COPY tts_api.py /app/

EXPOSE 8010

CMD ["python", "tts_api.py"]
```

```bash
# Build and run
docker build -t tts-service .
docker run -d -p 8010:8010 tts-service
```

---

## Integration Checklist

- [ ] TTS API running on correct host/port
- [ ] Backend can connect to TTS service
- [ ] Returns WAV format (not JSON)
- [ ] Audio plays in browser
- [ ] Response time < 5 seconds
- [ ] Error handling implemented
- [ ] Portuguese voice model configured
- [ ] Firewall allows connection
- [ ] Service starts on boot (systemd/docker)

---

## Support

For issues or questions:
- Check logs: `/opt/virtualasistant/backend/logs/django.log`
- Enable debug logging in Django settings
- Test TTS service independently before integration




# Coqui TTS Service API Documentation

This document describes the API interface that the Coqui TTS service must implement to integrate with the Virtual Assistant backend.

## Overview

The Virtual Assistant backend expects a REST API service that converts text to speech using Coqui TTS. The service should be accessible via HTTP POST requests.

## Endpoint

**URL**: Configurable via `TTS_SERVICE_URL` setting (default: `http://192.168.1.73:8010/api/tts/`)

**Method**: `POST`

**Content-Type**: `application/json`

## Request Format

### Headers
```
Content-Type: application/json
```

### Request Body
The request body must be a JSON object with the following structure:

```json
{
  "text": "O texto a ser convertido em fala"
}
```

**Fields:**
- `text` (string, required): The text to convert to speech (in Portuguese)

### Example Request
```bash
curl -X POST http://192.168.1.73:8010/api/tts/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá, como estás?"}'
```

## Response Format

### Success Response

**Status Code**: `200 OK`

**Content-Type**: `audio/wav` (or appropriate audio MIME type)

**Body**: Raw audio data as bytes (WAV format recommended)

The backend expects to receive the audio file content directly in the response body as binary data.

### Error Response

**Status Code**: `4xx` or `5xx` (e.g., `400 Bad Request`, `500 Internal Server Error`)

**Content-Type**: `application/json` or `text/plain`

**Body**: Error message (optional, for logging purposes)

Example error response:
```json
{
  "error": "Failed to generate speech: Model not found"
}
```

## Audio Format Requirements

- **Format**: WAV (recommended) or any format that can be played in browsers
- **Sample Rate**: 22050 Hz or 44100 Hz (common for TTS)
- **Channels**: Mono (1 channel) or Stereo (2 channels)
- **Bit Depth**: 16-bit (standard)

The backend will accept the audio format as returned by the service, but WAV format is preferred for compatibility.

## Timeout

The backend has a **10-second timeout** for TTS requests. The service should respond within this timeframe. For longer text, consider:

1. Streaming the response
2. Processing in chunks
3. Returning an error if processing takes too long

## Implementation Notes

### Python/Flask Example

```python
from flask import Flask, request, Response
import io
from TTS.api import TTS

app = Flask(__name__)
tts = TTS(model_name="tts_models/pt/cv/vits", progress_bar=False)

@app.route('/api/tts/', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return {'error': 'Text is required'}, 400
        
        # Generate speech
        wav = tts.tts(text=text)
        
        # Convert to bytes (numpy array to WAV bytes)
        import soundfile as sf
        import io
        buffer = io.BytesIO()
        sf.write(buffer, wav, 22050, format='WAV')
        buffer.seek(0)
        
        return Response(
            buffer.read(),
            mimetype='audio/wav',
            status=200
        )
        
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8010)
```

### Python/FastAPI Example

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from TTS.api import TTS
import soundfile as sf
import io
import numpy as np

app = FastAPI()
tts = TTS(model_name="tts_models/pt/cv/vits", progress_bar=False)

class TTSRequest(BaseModel):
    text: str

@app.post("/api/tts/")
async def synthesize(request: TTSRequest):
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Generate speech
        wav = tts.tts(text=request.text)
        
        # Convert numpy array to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, wav, 22050, format='WAV')
        buffer.seek(0)
        
        return Response(
            content=buffer.read(),
            media_type='audio/wav',
            status_code=200
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Backend Integration

The backend code (`tts_service.py`) expects:

1. **POST request** to the configured URL
2. **JSON body** with `text` field
3. **200 status** with audio bytes in response body
4. **10-second timeout** maximum

The backend function:
```python
def generate_speech(text: str) -> Optional[bytes]:
    response = requests.post(
        tts_url,
        json={'text': text},
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    if response.status_code == 200:
        return response.content  # Raw audio bytes
    else:
        return None
```

## Testing

Test the service with:

```bash
# Simple test
curl -X POST http://192.168.1.73:8010/api/tts/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Olá, esta é uma mensagem de teste"}' \
  --output test_audio.wav

# Play the audio (Linux)
aplay test_audio.wav
# Or (macOS)
afplay test_audio.wav
```

## Configuration

The backend uses Django settings to configure the TTS service URL:

```python
# settings.py or .env
TTS_SERVICE_URL = 'http://192.168.1.73:8010/api/tts/'
```

Make sure this URL is accessible from the backend container.

## Error Handling

The backend handles errors gracefully:
- Network errors: Logs and returns `None`
- HTTP errors: Logs status code and response, returns `None`
- Timeout: Logs timeout error, returns `None`

The service should return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing/invalid text)
- `500`: Internal server error (model failure, processing error)
- `503`: Service unavailable (if model is loading)

## Performance Considerations

1. **Model Loading**: Load the TTS model once at startup, not per request
2. **Caching**: Consider caching frequently used phrases
3. **Streaming**: For very long texts, consider streaming the audio response
4. **Concurrency**: Handle multiple concurrent requests if needed

## Security Considerations

1. **Input Validation**: Validate text length (prevent extremely long texts)
2. **Rate Limiting**: Consider rate limiting to prevent abuse
3. **Authentication**: Optional - add API key if needed
4. **CORS**: If accessed from browser, configure CORS appropriately









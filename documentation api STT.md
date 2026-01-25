# STT API Documentation

## Endpoint

**URL:** `http://192.168.1.68:8008/stt/transcribe`

**Method:** `POST`

**Content-Type:** `multipart/form-data`

## Request

### Query Parameters

- **language** (string, optional): Language code (default: "pt" for Portuguese)

### Form Data

- **file** (file, required): Audio file in any format (WebM/Opus/MP3/WAV/etc.)

### Example Request

```bash
curl -X POST "http://192.168.1.68:8008/stt/transcribe?language=pt" \
  -F "file=@audio.webm"
```

## Response

### Success Response

```json
{
  "text": "Transcribed text here"
}
```

### Error Response

The API may return an error status code (4xx/5xx) with an error message.

## Integration

The STT service is configured in `backend/config/settings.py`:

```python
STT_API_URL = os.getenv('STT_API_URL', 'http://192.168.1.68:8008')
```

The service automatically sends audio chunks to this endpoint and extracts the transcribed text from the response.


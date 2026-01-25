# Voice WebSocket Protocol Documentation

## Overview

The voice conversation mode uses WebSocket for full-duplex, real-time communication between the client and server. This enables:
- Continuous audio streaming (client → server)
- Real-time transcription updates (server → client)
- LLM response streaming (server → client)
- TTS audio chunks (server → client)
- Status updates (server → client)

## WebSocket Endpoint

```
ws://<host>/ws/voice/
wss://<host>/ws/voice/  (for HTTPS)
```

**Authentication**: WebSocket connection is authenticated via Django's session/JWT authentication. The connection will be rejected if the user is not authenticated.

## Connection Flow

1. **Client** establishes WebSocket connection
2. **Server** authenticates and accepts connection
3. **Server** sends `{"type": "status", "value": "connected"}`
4. **Client** sends `{"type": "start", ...}` to begin conversation
5. **Server** sends `{"type": "status", "value": "listening"}`
6. **Client** starts sending audio chunks (binary data)
7. **Server** processes audio and sends responses
8. **Client** sends `{"type": "stop"}` to end conversation
9. **Client** closes WebSocket connection

## Message Types

### Client → Server

#### Control Messages (JSON)

All control messages are sent as JSON strings.

##### Start Conversation

```json
{
  "type": "start",
  "conversation_id": "uuid-string",  // Optional: to continue a conversation
  "lang": "pt-PT"  // Language code
}
```

**Description**: Begins a voice conversation session. The server will start processing incoming audio chunks.

##### Stop Conversation

```json
{
  "type": "stop"
}
```

**Description**: Ends the current conversation session. The server will stop processing audio.

##### Ping (Heartbeat)

```json
{
  "type": "ping"
}
```

**Description**: Heartbeat message to keep the connection alive. Server responds with `pong`.

#### Audio Data (Binary)

Audio chunks are sent as **binary WebSocket messages** (not JSON).

- **Format**: WebM/Opus (from browser `MediaRecorder`)
- **Frequency**: Chunks sent every ~500ms (configurable via `MediaRecorder.start(timeslice)`)
- **Codec**: Opus at 48kHz (recommended for voice)

**Example (JavaScript)**:
```javascript
const mediaRecorder = new MediaRecorder(stream, { 
  mimeType: 'audio/webm;codecs=opus' 
});

mediaRecorder.ondataavailable = (event) => {
  if (event.data.size > 0) {
    websocket.send(event.data);  // Send binary blob
  }
};

mediaRecorder.start(500);  // 500ms chunks
```

---

### Server → Client

All server messages are sent as JSON strings.

#### Status Update

```json
{
  "type": "status",
  "value": "listening" | "thinking" | "speaking" | "error" | "connected" | "stopped"
}
```

**Description**: Indicates the current state of the conversation.

- `connected`: WebSocket connection established
- `listening`: Server is actively listening for audio
- `thinking`: Server is processing (STT + LLM)
- `speaking`: Server is generating/sending TTS audio
- `error`: An error occurred
- `stopped`: Conversation has stopped

#### Partial Transcript

```json
{
  "type": "partial_transcript",
  "text": "partial transcription..."
}
```

**Description**: Intermediate transcription result (if supported by STT engine). May update multiple times before final transcript.

#### Final Transcript

```json
{
  "type": "final_transcript",
  "text": "final user transcription"
}
```

**Description**: Final transcription of the user's speech. This is what was understood by the STT engine.

#### LLM Text Delta

```json
{
  "type": "llm_text_delta",
  "text": "chunk of response"
}
```

**Description**: Streaming chunk of the LLM's response. Multiple deltas will be sent as the LLM generates the response in real-time.

**Client handling**:
```javascript
// Accumulate deltas
fullResponse += data.text;
```

#### LLM Text Final

```json
{
  "type": "llm_text_final",
  "text": "complete LLM response"
}
```

**Description**: Complete LLM response text. Sent after all deltas.

#### TTS Audio Chunk

```json
{
  "type": "tts_audio_chunk",
  "format": "audio/wav" | "audio/ogg",
  "data_b64": "base64-encoded-audio-data"
}
```

**Description**: Audio chunk from TTS (Text-to-Speech) conversion of the LLM response.

- **Format**: Typically WAV or OGG/Opus
- **Encoding**: Base64-encoded binary audio data
- **Playback**: Client should decode and play immediately (queue if necessary)

**Client handling**:
```javascript
// Decode base64
const binaryString = atob(data.data_b64);
const bytes = new Uint8Array(binaryString.length);
for (let i = 0; i < binaryString.length; i++) {
  bytes[i] = binaryString.charCodeAt(i);
}

// Decode and play with Web Audio API
const audioBuffer = await audioContext.decodeAudioData(bytes.buffer);
const source = audioContext.createBufferSource();
source.buffer = audioBuffer;
source.connect(audioContext.destination);
source.start();
```

#### Error

```json
{
  "type": "error",
  "message": "error description"
}
```

**Description**: An error occurred during processing.

#### Pong (Heartbeat Response)

```json
{
  "type": "pong"
}
```

**Description**: Response to client's `ping` message.

---

## Typical Conversation Flow

```
[Client] Connect WebSocket
[Server] → {"type": "status", "value": "connected"}

[Client] → {"type": "start", "conversation_id": "...", "lang": "pt-PT"}
[Server] → {"type": "status", "value": "listening"}

[Client] → (binary audio chunk)
[Client] → (binary audio chunk)
[Client] → (binary audio chunk)
...

[Server] → {"type": "status", "value": "thinking"}
[Server] → {"type": "final_transcript", "text": "Olá, como estás?"}

[Server] → {"type": "llm_text_delta", "text": "Olá! "}
[Server] → {"type": "llm_text_delta", "text": "Estou bem"}
[Server] → {"type": "llm_text_delta", "text": ", obrigado!"}
[Server] → {"type": "llm_text_final", "text": "Olá! Estou bem, obrigado!"}

[Server] → {"type": "status", "value": "speaking"}
[Server] → {"type": "tts_audio_chunk", "format": "audio/wav", "data_b64": "..."}

[Server] → {"type": "status", "value": "listening"}

[Client] → (more audio chunks...)
...

[Client] → {"type": "stop"}
[Server] → {"type": "status", "value": "stopped"}
[Client] Close WebSocket
```

---

## Error Handling

### Client-Side Errors

- **Microphone permission denied**: Show error to user, cannot start conversation
- **WebSocket connection failed**: Retry with exponential backoff or show error
- **Audio encoding not supported**: Show error, browser may not support WebM/Opus

### Server-Side Errors

- **STT failure**: Server sends `{"type": "error", "message": "Transcription failed"}`
- **LLM failure**: Server sends `{"type": "error", "message": "LLM error"}`
- **TTS failure**: Server may skip TTS and only send text response
- **Authentication failure**: WebSocket connection rejected with close code `4001`

### Disconnection Handling

- **Client disconnects**: Server cleans up audio buffers, stops processing
- **Server disconnects**: Client should show error and allow user to reconnect
- **Network interruption**: Client should detect disconnection and allow reconnection

---

## Security Considerations

1. **Authentication**: WebSocket connection requires authenticated user session
2. **Rate limiting**: Consider implementing rate limiting to prevent abuse
3. **Audio size limits**: Limit accumulated audio buffer size per session
4. **Timeout**: Implement session timeout for idle connections
5. **CORS/Origin check**: Validate WebSocket origin matches expected domain

---

## Performance Optimization

1. **Audio chunking**: Send 500ms chunks for balance between latency and bandwidth
2. **VAD (Voice Activity Detection)**: Process audio after detecting end of speech
3. **Streaming LLM**: Stream LLM response to reduce perceived latency
4. **Chunked TTS**: Generate and send TTS in chunks (if supported)
5. **Connection pooling**: Reuse connections for multiple conversations

---

## Browser Compatibility

### Required APIs

- **WebSocket**: All modern browsers
- **MediaRecorder**: Chrome 47+, Firefox 25+, Safari 14.1+
- **getUserMedia**: Chrome 53+, Firefox 36+, Safari 11+
- **Web Audio API**: All modern browsers

### Fallback

If `MediaRecorder` with `audio/webm;codecs=opus` is not supported, try:
1. `audio/webm` (without codec specification)
2. `audio/ogg;codecs=opus`
3. `audio/mp4` (on Safari)

---

## Testing

### Manual Testing

1. Open browser console
2. Navigate to conversation page
3. Click "Ligar" (Start)
4. Grant microphone permission
5. Speak into microphone
6. Observe:
   - WebSocket connection status
   - Transcription appearing
   - LLM response text
   - TTS audio playback
   - Status changes

### WebSocket Testing Tools

- **Browser DevTools**: Network tab → WS filter → Inspect messages
- **Postman**: Supports WebSocket connections
- **wscat**: Command-line WebSocket client

**Example with wscat**:
```bash
wscat -c "ws://localhost:1080/ws/voice/"
# (Note: Authentication required, use browser session cookie)
```

---

## Future Enhancements

1. **WebRTC**: For lower latency and peer-to-peer audio
2. **Partial STT**: Stream transcription results as they arrive
3. **Interrupt handling**: Allow user to interrupt assistant mid-response
4. **Multi-language**: Support language switching mid-conversation
5. **Emotion detection**: Analyze tone and emotion in voice
6. **Background noise filtering**: Advanced noise cancellation

---

## References

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [WebSocket Protocol (RFC 6455)](https://tools.ietf.org/html/rfc6455)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
















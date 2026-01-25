"""
WebSocket consumers for real-time voice conversation.
"""
import json
import base64
import asyncio
import logging
from typing import Optional, List
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async

from .services.stt_service import transcribe_audio, detect_silence
from .services.ollama_client import stream_ollama_chat, build_messages
from .services.tts_service import generate_speech
from .models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class VoiceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for voice conversation mode.
    
    Protocol:
    - Client sends JSON control messages and binary audio chunks
    - Server responds with JSON events and binary audio chunks
    
    Control messages (JSON):
    - {"type": "start", "conversation_id": "uuid", "lang": "pt-PT"}
    - {"type": "stop"}
    - {"type": "ping"}
    
    Server events (JSON):
    - {"type": "status", "value": "listening|thinking|speaking|error"}
    - {"type": "partial_transcript", "text": "..."}
    - {"type": "final_transcript", "text": "..."}
    - {"type": "llm_text_delta", "text": "..."}
    - {"type": "llm_text_final", "text": "..."}
    - {"type": "tts_audio_chunk", "format": "audio/ogg", "data_b64": "..."}
    - {"type": "error", "message": "..."}
    
    Audio format: WebM/Opus chunks from browser MediaRecorder
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: Optional[User] = None
        self.conversation_id: Optional[str] = None
        self.conversation_db_id: Optional[int] = None  # Integer ID for DB queries
        self.language: str = "pt"
        self.is_active: bool = False
        self.audio_chunks: List[bytes] = []
        self.processing: bool = False
        
    async def connect(self):
        """
        Handle WebSocket connection.
        Authenticate user and accept connection.
        """
        try:
            # Get user from scope (set by AuthMiddlewareStack)
            self.user = self.scope.get("user")
            
            if not self.user or not self.user.is_authenticated:
                logger.warning("Unauthenticated WebSocket connection attempt")
                await self.close(code=4001)
                return
            
            # Accept the connection
            await self.accept()
            
            logger.info(f"Voice WebSocket connected: user={self.user.username}")
            
            # Send initial status
            await self.send_json_event({
                "type": "status",
                "value": "connected"
            })
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        """
        logger.info(f"Voice WebSocket disconnected: user={self.user.username if self.user else 'unknown'}, code={close_code}")
        self.is_active = False
        self.audio_chunks.clear()
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages (JSON control or binary audio).
        """
        try:
            if text_data:
                # JSON control message
                await self.handle_control_message(text_data)
            elif bytes_data:
                # Binary audio chunk
                await self.handle_audio_chunk(bytes_data)
                
        except Exception as e:
            logger.error(f"Error receiving WebSocket data: {e}")
            await self.send_error("Internal server error")
    
    async def handle_control_message(self, text_data: str):
        """
        Handle JSON control messages from client.
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            
            if msg_type == "start":
                await self.handle_start(data)
            elif msg_type == "stop":
                await self.handle_stop()
            elif msg_type == "ping":
                await self.send_json_event({"type": "pong"})
            else:
                logger.warning(f"Unknown control message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in control message: {e}")
            await self.send_error("Invalid JSON")
    
    async def handle_start(self, data: dict):
        """
        Handle start message - begin voice conversation.
        """
        # Create a new conversation for this voice session
        conversation = await database_sync_to_async(Conversation.objects.create)(
            user=self.user,
            title="Voice Conversation"
        )
        self.conversation_id = str(conversation.id)  # Store as string for consistency
        self.conversation_db_id = conversation.id  # Store integer ID for DB queries
        self.language = data.get("lang", "pt-PT").split("-")[0]  # Extract language code
        self.is_active = True
        self.audio_chunks.clear()
        
        logger.info(f"Voice conversation started: user={self.user.username}, conv={self.conversation_db_id}, lang={self.language}")
        
        await self.send_json_event({
            "type": "status",
            "value": "listening"
        })
    
    async def handle_stop(self):
        """
        Handle stop message - end voice conversation.
        """
        self.is_active = False
        self.audio_chunks.clear()
        
        logger.info(f"Voice conversation stopped: user={self.user.username}")
        
        await self.send_json_event({
            "type": "status",
            "value": "stopped"
        })
    
    async def handle_audio_chunk(self, audio_data: bytes):
        """
        Handle incoming audio chunk.
        Accumulate chunks and process when we have enough.
        """
        if not self.is_active:
            logger.warning("Received audio chunk while not active")
            return
        
        if self.processing:
            # Skip chunks while processing previous audio
            return
        
        # Accumulate audio chunks
        self.audio_chunks.append(audio_data)
        
        logger.debug(f"Received audio chunk: {len(audio_data)} bytes, total chunks: {len(self.audio_chunks)}")
        
        # Check if we should process (simple VAD based on chunk count)
        # In production, use proper VAD or silence detection
        if detect_silence(self.audio_chunks, threshold=5):  # ~2.5 seconds at 500ms chunks
            await self.process_accumulated_audio()
    
    async def process_accumulated_audio(self):
        """
        Process accumulated audio chunks:
        1. Combine chunks
        2. Transcribe (STT)
        3. Get LLM response
        4. Generate speech (TTS)
        5. Send to client
        """
        if self.processing or not self.audio_chunks:
            return
        
        self.processing = True
        
        try:
            # WebM chunks from MediaRecorder are fragments that need to be combined
            # While simple concatenation isn't perfect, ffmpeg on the STT server can often handle it
            # We'll combine all chunks and let ffmpeg try to process it
            if not self.audio_chunks:
                self.processing = False
                return
            
            # Store chunk count for logging before clearing
            chunk_count = len(self.audio_chunks)
            
            # Combine all chunks (ffmpeg may be able to handle the concatenated fragments)
            combined_audio = b''.join(self.audio_chunks)
            self.audio_chunks.clear()
            
            # Validate minimum audio size - need enough data for a valid audio stream
            # MediaRecorder typically sends ~26KB chunks every 500ms, so 5 chunks = ~130KB
            # We'll accept anything above 50KB as it likely contains multiple chunks
            MIN_AUDIO_SIZE = 50 * 1024  # 50KB minimum (roughly 2+ chunks)
            if len(combined_audio) < MIN_AUDIO_SIZE:
                logger.warning(f"Audio too small ({len(combined_audio)} bytes < {MIN_AUDIO_SIZE} bytes), skipping transcription (need more chunks)")
                self.processing = False
                return
            
            logger.info(f"Processing audio: {len(combined_audio)} bytes (combined {chunk_count} chunks)")
            
            # Update status
            await self.send_json_event({
                "type": "status",
                "value": "thinking"
            })
            
            # Step 1: Transcribe audio (STT)
            transcript = await self.transcribe_audio(combined_audio)
            
            if not transcript:
                logger.warning("No transcript from STT, skipping processing")
                await self.send_json_event({
                    "type": "error",
                    "message": "Não foi possível transcrever o áudio. Tenta novamente."
                })
                return
            
            # Send final transcript to client
            await self.send_json_event({
                "type": "final_transcript",
                "text": transcript
            })
            
            logger.info(f"Transcript: {transcript}")
            
            # Step 2: Get conversation context and build messages
            messages = await self.build_conversation_messages(transcript)
            
            # Step 3: Stream LLM response
            full_response = ""
            reply_text = ""
            async for chunk_dict in self.stream_llm_response(messages):
                chunk_type = chunk_dict.get('type')
                
                if chunk_type == 'chunk' and 'content' in chunk_dict:
                    # During streaming, accumulate JSON being built
                    # Don't send to client yet - wait for parsed reply
                    text_chunk = chunk_dict['content']
                    full_response += text_chunk
                    
                elif chunk_type == 'done' and 'reply' in chunk_dict:
                    # Final parsed reply - use this for display and TTS
                    reply_text = chunk_dict['reply']
                    logger.info(f"LLM reply extracted: {reply_text[:100]}...")
                    
                    # Send final text to client (only the reply text, not JSON)
                    await self.send_json_event({
                        "type": "llm_text_final",
                        "text": reply_text
                    })
                    break
                    
                elif chunk_type == 'error':
                    error_msg = chunk_dict.get('error', 'Unknown error')
                    logger.error(f"LLM streaming error: {error_msg}")
                    await self.send_error(f"Erro ao processar resposta: {error_msg}")
                    return
            
            # If we didn't get a 'done' event, try to extract reply from accumulated JSON
            if not reply_text and full_response:
                try:
                    import json
                    from .services.ollama_client import extract_json_from_text
                    json_str = extract_json_from_text(full_response)
                    if json_str:
                        data = json.loads(json_str)
                        reply_text = data.get('reply', '')
                        logger.info(f"Extracted reply from JSON: {reply_text[:100]}...")
                        
                        # Send final text to client
                        await self.send_json_event({
                            "type": "llm_text_final",
                            "text": reply_text
                        })
                    else:
                        # No JSON found, use full response as fallback
                        reply_text = full_response
                        await self.send_json_event({
                            "type": "llm_text_final",
                            "text": reply_text
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract reply from response: {e}, using full response")
                    reply_text = full_response
                    await self.send_json_event({
                        "type": "llm_text_final",
                        "text": reply_text
                    })
            
            # Use reply_text for TTS (not the raw JSON)
            if not reply_text:
                reply_text = full_response
            
            logger.info(f"Final LLM response text: {reply_text[:100]}...")
            
            # Step 4: Generate speech (TTS) - use reply_text, not the raw JSON
            await self.send_json_event({
                "type": "status",
                "value": "speaking"
            })
            
            audio_data = await self.generate_speech(reply_text)
            
            if audio_data:
                # Send audio chunk (base64 encoded for JSON)
                await self.send_json_event({
                    "type": "tts_audio_chunk",
                    "format": "audio/wav",
                    "data_b64": base64.b64encode(audio_data).decode('utf-8')
                })
            
            # Step 5: Save conversation to database - use reply_text
            await self.save_conversation_message(transcript, reply_text)
            
            # Back to listening
            await self.send_json_event({
                "type": "status",
                "value": "listening"
            })
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            await self.send_error(f"Processing error: {str(e)}")
            
        finally:
            self.processing = False
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio using STT service (async wrapper).
        """
        return await sync_to_async(transcribe_audio)(audio_data, self.language)
    
    async def build_conversation_messages(self, user_message: str) -> list:
        """
        Build messages array for LLM, including conversation history.
        """
        # Get conversation history if conversation_db_id exists
        history = []
        if self.conversation_db_id:
            try:
                conversation = await database_sync_to_async(Conversation.objects.get)(
                    id=self.conversation_db_id,
                    user=self.user
                )
                messages = await database_sync_to_async(list)(
                    conversation.messages.all().order_by('created_at')
                )
                history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
            except Conversation.DoesNotExist:
                logger.warning(f"Conversation {self.conversation_db_id} not found, using empty history")
        
        return await sync_to_async(build_messages)(
            history=history,
            user_message=user_message,
            user=self.user
        )
    
    async def stream_llm_response(self, messages: list):
        """
        Stream LLM response (async generator).
        """
        # Wrap the sync generator in async
        for chunk in await sync_to_async(list)(stream_ollama_chat(messages)):
            yield chunk
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)
    
    async def generate_speech(self, text: str) -> Optional[bytes]:
        """
        Generate speech from text using TTS service (async wrapper).
        """
        return await sync_to_async(generate_speech)(text)
    
    @database_sync_to_async
    def save_conversation_message(self, user_text: str, assistant_text: str):
        """
        Save conversation message to database.
        """
        try:
            # Get or create conversation
            if self.conversation_db_id:
                try:
                    conversation = Conversation.objects.get(
                        id=self.conversation_db_id,
                        user=self.user
                    )
                except Conversation.DoesNotExist:
                    conversation = Conversation.objects.create(
                        user=self.user,
                        title=user_text[:100]  # Use first part as title
                    )
                    self.conversation_db_id = conversation.id
                    self.conversation_id = str(conversation.id)
            else:
                conversation = Conversation.objects.create(
                    user=self.user,
                    title=user_text[:100]
                )
                self.conversation_db_id = conversation.id
                self.conversation_id = str(conversation.id)
            
            # Save user message
            ConversationMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_text
            )
            
            # Save assistant message
            ConversationMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=assistant_text
            )
            
            logger.info(f"Saved conversation messages: conv={conversation.id}")
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    async def send_json_event(self, event: dict):
        """
        Send JSON event to client.
        """
        await self.send(text_data=json.dumps(event))
    
    async def send_error(self, message: str):
        """
        Send error event to client.
        """
        await self.send_json_event({
            "type": "error",
            "message": message
        })
        
        await self.send_json_event({
            "type": "status",
            "value": "error"
        })


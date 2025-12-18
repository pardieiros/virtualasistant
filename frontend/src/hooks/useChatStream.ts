/**
 * Custom hook for consuming SSE streaming chat from Django backend.
 * 
 * Usage:
 * ```tsx
 * const { sendMessage, messages, isStreaming, error } = useChatStream();
 * 
 * // Send a message
 * await sendMessage('Hello!', history);
 * ```
 */

import { useState, useCallback, useRef } from 'react';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface StreamingState {
  isStreaming: boolean;
  error: string | null;
  action: any | null;
}

export interface UseChatStreamReturn {
  sendMessage: (message: string, history?: ChatMessage[], conversationId?: number) => Promise<void>;
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  action: any | null;
  cancelStream: () => void;
  currentStreamingMessage: string;
}

/**
 * Hook for SSE-based streaming chat.
 */
export const useChatStream = (): UseChatStreamReturn => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<any | null>(null);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  
  // Keep reference to EventSource for cancellation
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancelStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(async (
    message: string,
    history: ChatMessage[] = [],
    conversationId?: number
  ) => {
    // Reset state
    setError(null);
    setAction(null);
    setCurrentStreamingMessage('');
    setIsStreaming(true);

    // Add user message immediately
    const userMessage: ChatMessage = { role: 'user', content: message };
    setMessages(prev => [...prev, userMessage]);

    // Get auth token
    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('Authentication required');
      setIsStreaming(false);
      return;
    }

    try {
      // Use fetch with ReadableStream for POST requests (EventSource only supports GET)
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      const response = await fetch('/api/chat/stream/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message,
          history,
          conversation_id: conversationId,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      // Read stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let streamingContent = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }

        // Decode chunk
        buffer += decoder.decode(value, { stream: true });

        // Process SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6); // Remove 'data: ' prefix
            
            try {
              const data = JSON.parse(dataStr);

              if (data.type === 'chunk') {
                // Append chunk to streaming content
                streamingContent += data.content;
                setCurrentStreamingMessage(streamingContent);
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', dataStr);
            }
          } else if (line.startsWith('event: ')) {
            // Parse event type (handled in next loop)
            // Next line should be data
            continue;
          }
        }

        // Handle special events (done, action, error, final_text)
        // These come with 'event: ' prefix
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          
          if (line.startsWith('event: done')) {
            // Stream finished
            if (i + 1 < lines.length && lines[i + 1].startsWith('data: ')) {
              const dataStr = lines[i + 1].slice(6);
              try {
                const data = JSON.parse(dataStr);
                console.log('Stream done:', data);
              } catch (e) {
                // Ignore
              }
            }
            
            // Add final assistant message
            setMessages(prev => [
              ...prev,
              { role: 'assistant', content: streamingContent }
            ]);
            setCurrentStreamingMessage('');
            setIsStreaming(false);
          } else if (line.startsWith('event: action')) {
            // Action detected
            if (i + 1 < lines.length && lines[i + 1].startsWith('data: ')) {
              const dataStr = lines[i + 1].slice(6);
              try {
                const data = JSON.parse(dataStr);
                setAction(data.action);
                console.log('Action received:', data.action);
              } catch (e) {
                console.warn('Failed to parse action data');
              }
            }
          } else if (line.startsWith('event: error')) {
            // Error occurred
            if (i + 1 < lines.length && lines[i + 1].startsWith('data: ')) {
              const dataStr = lines[i + 1].slice(6);
              try {
                const data = JSON.parse(dataStr);
                setError(data.error || 'Unknown error');
                setIsStreaming(false);
              } catch (e) {
                setError('Stream error');
                setIsStreaming(false);
              }
            }
          } else if (line.startsWith('event: final_text')) {
            // Final clean text (ACTION line removed)
            if (i + 1 < lines.length && lines[i + 1].startsWith('data: ')) {
              const dataStr = lines[i + 1].slice(6);
              try {
                const data = JSON.parse(dataStr);
                // Replace streaming content with clean text
                streamingContent = data.text;
                setCurrentStreamingMessage(streamingContent);
              } catch (e) {
                console.warn('Failed to parse final_text data');
              }
            }
          }
        }
      }

      abortControllerRef.current = null;

    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream cancelled by user');
      } else {
        console.error('Stream error:', err);
        setError(err.message || 'Failed to stream chat');
      }
      setIsStreaming(false);
    }
  }, []);

  return {
    sendMessage,
    messages,
    isStreaming,
    error,
    action,
    cancelStream,
    currentStreamingMessage,
  };
};


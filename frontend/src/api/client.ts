import axios from 'axios';
import type { 
  ShoppingItem, 
  AgendaEvent, 
  Note, 
  HomeAssistantConfig,
  ChatMessage,
  ChatResponse,
  TokenResponse,
  UserNotificationPreferences,
  TerminalAPIConfig,
  Conversation,
  ConversationMessage,
  TodoItem,
  VideoTranscription
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const response = await apiClient.post('/auth/token/', { username, password });
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Shopping Items API
export const shoppingAPI = {
  list: async (params?: { status?: string; store?: string; search?: string }): Promise<ShoppingItem[]> => {
    const response = await apiClient.get('/shopping-items/', { params });
    return response.data.results || response.data;
  },
  
  create: async (item: Partial<ShoppingItem>): Promise<ShoppingItem> => {
    const response = await apiClient.post('/shopping-items/', item);
    return response.data;
  },
  
  update: async (id: number, item: Partial<ShoppingItem>): Promise<ShoppingItem> => {
    const response = await apiClient.patch(`/shopping-items/${id}/`, item);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/shopping-items/${id}/`);
  },
};

// Agenda API
export const agendaAPI = {
  list: async (params?: { start_date?: string; end_date?: string }): Promise<AgendaEvent[]> => {
    const response = await apiClient.get('/agenda/', { params });
    return response.data.results || response.data;
  },
  
  create: async (event: Partial<AgendaEvent>): Promise<AgendaEvent> => {
    const response = await apiClient.post('/agenda/', event);
    return response.data;
  },
  
  update: async (id: number, event: Partial<AgendaEvent>): Promise<AgendaEvent> => {
    const response = await apiClient.patch(`/agenda/${id}/`, event);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/agenda/${id}/`);
  },
};

// Notes API
export const notesAPI = {
  list: async (): Promise<Note[]> => {
    const response = await apiClient.get('/notes/');
    return response.data.results || response.data;
  },
  
  create: async (text: string): Promise<Note> => {
    const response = await apiClient.post('/notes/', { text });
    return response.data;
  },
  
  update: async (id: number, text: string): Promise<Note> => {
    const response = await apiClient.patch(`/notes/${id}/`, { text });
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/notes/${id}/`);
  },
};

// Todo API
export const todoAPI = {
  list: async (params?: { status?: string; priority?: string }): Promise<TodoItem[]> => {
    const response = await apiClient.get('/todos/', { params });
    return response.data.results || response.data;
  },
  
  create: async (todo: Partial<TodoItem>): Promise<TodoItem> => {
    const response = await apiClient.post('/todos/', todo);
    return response.data;
  },
  
  update: async (id: number, todo: Partial<TodoItem>): Promise<TodoItem> => {
    const response = await apiClient.patch(`/todos/${id}/`, todo);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/todos/${id}/`);
  },
};

// Chat API
export const chatAPI = {
  send: async (message: string, history: ChatMessage[] = [], conversationId?: number): Promise<ChatResponse> => {
    const response = await apiClient.post('/chat/', { message, history, conversation_id: conversationId });
    return response.data;
  },
};

// Home Assistant API
export const homeAssistantAPI = {
  getConfig: async (): Promise<HomeAssistantConfig | null> => {
    try {
      const response = await apiClient.get('/homeassistant/my_config/');
      return response.data;
    } catch {
      return null;
    }
  },
  
  updateConfig: async (config: Partial<HomeAssistantConfig>): Promise<HomeAssistantConfig> => {
    const response = await apiClient.post('/homeassistant/my_config/', config);
    return response.data;
  },
  
  getAreasAndDevices: async (): Promise<any> => {
    const response = await apiClient.get('/homeassistant/areas_and_devices/');
    return response.data;
  },
  
  controlDevice: async (entityId: string, domain: string, service: string, data?: any): Promise<any> => {
    const response = await apiClient.post('/homeassistant/control_device/', {
      entity_id: entityId,
      domain,
      service,
      data: data || {},
    });
    return response.data;
  },
  
  getDeviceAliases: async (): Promise<any[]> => {
    const response = await apiClient.get('/device-aliases/');
    return response.data;
  },
  
  createDeviceAlias: async (alias: { entity_id: string; alias: string; area?: string }): Promise<any> => {
    const response = await apiClient.post('/device-aliases/', alias);
    return response.data;
  },
  
  updateDeviceAlias: async (id: number, alias: Partial<{ alias: string; area: string }>): Promise<any> => {
    const response = await apiClient.patch(`/device-aliases/${id}/`, alias);
    return response.data;
  },
  
  deleteDeviceAlias: async (id: number): Promise<void> => {
    await apiClient.delete(`/device-aliases/${id}/`);
  },
};

// Push Subscription API
export const pushSubscriptionAPI = {
  register: async (subscription: { endpoint: string; keys: { p256dh: string; auth: string } }): Promise<void> => {
    await apiClient.post('/push-subscriptions/register/', subscription);
  },
  
  unregister: async (endpoint: string): Promise<void> => {
    await apiClient.post('/push-subscriptions/unregister/', { endpoint });
  },
  
  getVapidPublicKey: async (): Promise<{ public_key: string }> => {
    const response = await apiClient.get('/push-subscriptions/vapid_public_key/');
    return response.data;
  },
  
  test: async (): Promise<{ success: boolean; message: string; errors?: string[] }> => {
    const response = await apiClient.post('/push-subscriptions/test/', {});
    return response.data;
  },
};

// Text-to-Speech API
export const ttsAPI = {
  /**
   * Generate speech audio from text using backend TTS service
   * @param text Text to convert to speech
   * @returns Audio blob
   */
  generate: async (text: string): Promise<Blob> => {
    const response = await apiClient.post<{ audio: string; format: string; size: number }>(
      '/tts/',
      { text }
    );
    
    // Convert base64 to blob
    const audioBase64 = response.data.audio;
    const format = response.data.format || 'wav';
    
    // Decode base64 to binary
    const byteCharacters = atob(audioBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    
    // Create blob from binary data
    return new Blob([byteArray], { type: `audio/${format}` });
  },
};

// Notification Preferences API
export const notificationPreferencesAPI = {
  getPreferences: async (): Promise<UserNotificationPreferences | null> => {
    try {
      const response = await apiClient.get('/notification-preferences/my_preferences/');
      return response.data;
    } catch {
      return null;
    }
  },
  
  updatePreferences: async (preferences: Partial<UserNotificationPreferences>): Promise<UserNotificationPreferences> => {
    const response = await apiClient.post('/notification-preferences/my_preferences/', preferences);
    return response.data;
  },
};

// Terminal API Config
export const terminalAPI = {
  getConfig: async (): Promise<TerminalAPIConfig | null> => {
    try {
      const response = await apiClient.get('/terminal-api/my_config/');
      return response.data;
    } catch {
      return null;
    }
  },
  
  updateConfig: async (config: Partial<TerminalAPIConfig & { api_token?: string }>): Promise<TerminalAPIConfig> => {
    const response = await apiClient.post('/terminal-api/my_config/', config);
    return response.data;
  },
};

// Conversations API
export const conversationsAPI = {
  list: async (): Promise<Conversation[]> => {
    const response = await apiClient.get('/conversations/');
    return response.data.results || response.data;
  },
  
  get: async (id: number): Promise<Conversation> => {
    const response = await apiClient.get(`/conversations/${id}/`);
    return response.data;
  },
  
  create: async (title?: string, firstMessage?: string): Promise<Conversation> => {
    const response = await apiClient.post('/conversations/', { title, first_message: firstMessage });
    return response.data;
  },
  
  addMessage: async (conversationId: number, role: 'user' | 'assistant', content: string): Promise<ConversationMessage> => {
    const response = await apiClient.post(`/conversations/${conversationId}/add_message/`, { role, content });
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/conversations/${id}/`);
  },
};

// Video Upload API
export const videoAPI = {
  upload: async (file: File, onProgress?: (progress: number) => void): Promise<{ success: boolean; filename: string; message: string }> => {
    // For larger files, use chunked upload to avoid 504/502 and memory spikes.
    // Each chunk is small and finishes quickly, so proxies/timeouts are much less likely to fail.
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
    const CHUNK_THRESHOLD = 50 * 1024 * 1024; // 50MB

    const makeUploadId = (): string => {
      try {
        // Modern browsers
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
          return (crypto as any).randomUUID();
        }
      } catch {
        // ignore
      }
      // Fallback (not cryptographically strong, but OK as a session id)
      return `u_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    };

    if (file.size >= CHUNK_THRESHOLD) {
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
      const uploadId = makeUploadId();

      let lastResponse: any = null;

      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE;
        const end = Math.min(file.size, start + CHUNK_SIZE);
        const chunk = file.slice(start, end);

        lastResponse = await apiClient.post('/video/upload/chunk/', chunk, {
          headers: {
            'Content-Type': 'application/octet-stream',
            'X-Upload-Id': uploadId,
            'X-Chunk-Index': String(i),
            'X-Total-Chunks': String(totalChunks),
            'X-Filename': file.name,
          },
          timeout: 300000, // 5 minutes per chunk (should be plenty)
        });

        if (onProgress) {
          const percentCompleted = Math.round(((i + 1) * 100) / totalChunks);
          onProgress(percentCompleted);
        }
      }

      return lastResponse.data;
    }

    const formData = new FormData();
    formData.append('video', file);
    
    const token = localStorage.getItem('access_token');
    
    const response = await axios.post(`${API_BASE_URL}/video/upload/`, formData, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });
    
    return response.data;
  },
};

// STT API (Speech-to-Text Transcription) - All requests go through backend
export const sttAPI = {
  health: async (): Promise<any> => {
    const response = await apiClient.get('/stt/health/');
    return response.data;
  },
  
  createJob: async (filename: string, lang: string = 'pt', model: string = 'small', diarize: boolean = true): Promise<{ job_id: string; status: string }> => {
    const response = await apiClient.post('/stt/jobs/', {
      filename,
      lang,
      model,
      diarize,
    });
    return response.data;
  },
  
  getJobStatus: async (jobId: string): Promise<any> => {
    const response = await apiClient.get(`/stt/jobs/${jobId}/`);
    return response.data;
  },
  
  getJobResult: async (jobId: string): Promise<{ job_id: string; diarization: boolean; language: string; text: string }> => {
    const response = await apiClient.get(`/stt/jobs/${jobId}/result/`);
    return response.data;
  },
  
  subscribeToJobEvents: (jobId: string, onEvent: (event: any) => void): EventSource => {
    const token = localStorage.getItem('access_token');
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    // EventSource doesn't support custom headers, so we pass token as query parameter
    // The backend will validate it
    const url = token 
      ? `${apiBaseUrl}/stt/jobs/${jobId}/events/?token=${encodeURIComponent(token)}`
      : `${apiBaseUrl}/stt/jobs/${jobId}/events/`;
    
    const eventSource = new EventSource(url, {
      withCredentials: true,
    });
    
    eventSource.onmessage = (event) => {
      try {
        // SSE events can be in format "data: {...}" or just "{...}"
        let dataStr = event.data;
        if (dataStr.startsWith('data: ')) {
          dataStr = dataStr.substring(6);
        }
        const data = JSON.parse(dataStr);
        onEvent(data);
      } catch (error) {
        console.error('Error parsing SSE event:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };
    
    return eventSource;
  },
};

// Video Transcription API
export const videoTranscriptionAPI = {
  list: async (): Promise<VideoTranscription[]> => {
    const response = await apiClient.get('/video-transcriptions/');
    return response.data.results || response.data;
  },
  
  get: async (id: number): Promise<VideoTranscription> => {
    const response = await apiClient.get(`/video-transcriptions/${id}/`);
    return response.data;
  },
  
  create: async (data: {
    filename: string;
    transcription_text: string;
    language: string;
    diarization_enabled: boolean;
    speaker_mappings?: Record<string, string>;
  }): Promise<VideoTranscription> => {
    const response = await apiClient.post('/video-transcriptions/', data);
    return response.data;
  },
  
  updateSpeakers: async (id: number, speakerMappings: Record<string, string>): Promise<VideoTranscription> => {
    const response = await apiClient.patch(`/video-transcriptions/${id}/speakers/`, {
      speaker_mappings: speakerMappings,
    });
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/video-transcriptions/${id}/`);
  },
};

export default apiClient;


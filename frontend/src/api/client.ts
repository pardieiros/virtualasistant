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
  ConversationMessage
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

export default apiClient;


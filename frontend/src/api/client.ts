import axios from 'axios';
import type { 
  ShoppingItem, 
  AgendaEvent, 
  Note, 
  HomeAssistantConfig,
  ChatMessage,
  ChatResponse,
  TokenResponse
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
  send: async (message: string, history: ChatMessage[] = []): Promise<ChatResponse> => {
    const response = await apiClient.post('/chat/', { message, history });
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
};

export default apiClient;


export interface User {
  id: number;
  username: string;
  email: string;
}

export interface ShoppingItem {
  id: number;
  name: string;
  quantity: string;
  category: string;
  preferred_store: string;
  alternative_stores: string;
  notes: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'bought' | 'cancelled';
  created_at: string;
  updated_at: string;
}

export interface AgendaEvent {
  id: number;
  title: string;
  description: string;
  start_datetime: string;
  end_datetime: string | null;
  location: string;
  category: 'personal' | 'work' | 'health' | 'other';
  all_day: boolean;
  created_at: string;
}

export interface Note {
  id: number;
  text: string;
  created_at: string;
  updated_at: string;
}

export interface HomeAssistantConfig {
  id: number;
  base_url: string;
  enabled: boolean;
  token_configured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  reply: string;
  action: any;
  action_result: any;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}


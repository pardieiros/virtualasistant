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
  send_notification: boolean;
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
  isSearching?: boolean;
}

export interface ChatResponse {
  reply: string | null;
  action: any;
  action_result: any;
  search_in_progress?: boolean;
  via_pusher?: boolean;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface UserNotificationPreferences {
  agenda_events_enabled: boolean;
  agenda_reminder_minutes: number;
  shopping_updates_enabled: boolean;
  notes_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TerminalAPIConfig {
  id: number;
  api_url: string;
  enabled: boolean;
  token_configured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  message_count: number;
  messages?: ConversationMessage[];
  created_at: string;
  updated_at: string;
}

export interface TodoItem {
  id: number;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'completed' | 'cancelled';
  due_date: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}


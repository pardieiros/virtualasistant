import { useEffect, useRef } from 'react';
import Pusher from 'pusher-js';

// IMPORTANT: SOCKET_KEY must be the app_key (not app_id) for Soketi
// The Pusher constructor expects app_key as the first parameter
const SOCKET_HOST = import.meta.env.VITE_SOCKET_HOST || 'localhost';
const SOCKET_PORT = import.meta.env.VITE_SOCKET_PORT || '6001';
const SOCKET_KEY = import.meta.env.VITE_SOCKET_KEY || '';
const SOCKET_USE_TLS = import.meta.env.VITE_SOCKET_USE_TLS === 'true';

export const usePusher = (userId: number | null, onMessage: (event: string, data: any) => void) => {
  const pusherRef = useRef<Pusher | null>(null);
  const channelRef = useRef<any>(null);
  const onMessageRef = useRef(onMessage);
  const isInitializingRef = useRef(false);

  // Keep onMessage ref up to date without causing re-renders
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!userId || !SOCKET_KEY) {
      console.warn('Pusher: Missing userId or SOCKET_KEY', { userId, hasKey: !!SOCKET_KEY });
      return;
    }

    // Prevent multiple initializations
    if (isInitializingRef.current) {
      console.log('Pusher: Already initializing, skipping...');
      return;
    }

    // If we already have a pusher instance, don't create a new one
    if (pusherRef.current) {
      console.log('Pusher: Instance already exists, skipping initialization');
      return;
    }

    isInitializingRef.current = true;

    // Get API base URL from env or use default
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
    
    // Build auth endpoint - API_BASE_URL already includes /api, so just append the path
    const authEndpoint = API_BASE_URL.endsWith('/') 
      ? `${API_BASE_URL}pusher/auth/`
      : `${API_BASE_URL}/pusher/auth/`;
    
    console.log('Pusher: Initializing connection', {
      host: SOCKET_HOST,
      port: SOCKET_PORT,
      useTLS: SOCKET_USE_TLS,
      authEndpoint,
      keyLength: SOCKET_KEY.length,
    });
    
    const pusher = new Pusher(SOCKET_KEY, {
      cluster: '',
      wsHost: SOCKET_HOST,
      wsPort: parseInt(SOCKET_PORT),
      wssPort: parseInt(SOCKET_PORT),
      httpPath: '/app', // Soketi uses /app as the HTTP path
      enabledTransports: ['ws', 'wss'],
      forceTLS: SOCKET_USE_TLS,
      disableStats: true, // Disable stats for Soketi
      authEndpoint: authEndpoint,
      auth: {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      },
    });

    pusherRef.current = pusher;

    const channelName = `private-user-${userId}`;
    const channel = pusher.subscribe(channelName);
    
    // Handle subscription events
    channel.bind('pusher:subscription_error', (status: number) => {
      console.error('Pusher subscription error:', status);
      console.error('Pusher: Check that SOCKET_KEY is set to app_key (not app_id)');
    });
    
    channel.bind('pusher:subscription_succeeded', () => {
      console.log('Pusher: Subscription succeeded for channel', channelName);
      isInitializingRef.current = false;
    });
    
    // Handle connection events
    pusher.connection.bind('connected', () => {
      console.log('Pusher connected successfully');
      isInitializingRef.current = false;
    });
    
    pusher.connection.bind('disconnected', () => {
      console.log('Pusher disconnected');
      isInitializingRef.current = false;
    });
    
    pusher.connection.bind('error', (err: any) => {
      console.error('Pusher connection error:', err);
      isInitializingRef.current = false;
    });
    
    pusher.connection.bind('state_change', (states: any) => {
      console.log('Pusher state change:', states.previous, '->', states.current);
    });

    // Use ref to avoid re-binding on every render
    channel.bind('assistant-message', (data: any) => {
      console.log('[usePusher] Received assistant-message event on channel:', channelName);
      console.log('[usePusher] Event data:', data);
      console.log('[usePusher] Event data type:', typeof data);
      console.log('[usePusher] Event data keys:', data ? Object.keys(data) : 'null');
      
      // If data is a string, try to parse it as JSON
      let parsedData = data;
      if (typeof data === 'string') {
        try {
          parsedData = JSON.parse(data);
          console.log('[usePusher] Parsed JSON data:', parsedData);
        } catch (e) {
          console.warn('[usePusher] Failed to parse data as JSON:', e);
        }
      }
      
      onMessageRef.current('assistant-message', parsedData);
    });

    channel.bind('shopping-updated', (data: any) => {
      console.log('[usePusher] Received shopping-updated event:', data);
      onMessageRef.current('shopping-updated', data);
    });

    channel.bind('agenda-updated', (data: any) => {
      console.log('[usePusher] Received agenda-updated event:', data);
      onMessageRef.current('agenda-updated', data);
    });

    channelRef.current = channel;

    return () => {
      isInitializingRef.current = false;
      
      // Only cleanup if we're actually disconnecting
      if (channelRef.current) {
        try {
          channelRef.current.unbind_all();
          channelRef.current.unsubscribe();
        } catch (e) {
          console.warn('Pusher: Error during channel cleanup:', e);
        }
        channelRef.current = null;
      }
      
      if (pusherRef.current) {
        try {
          // Only disconnect if we're not already disconnected
          if (pusherRef.current.connection.state !== 'disconnected') {
            pusherRef.current.disconnect();
          }
        } catch (e) {
          console.warn('Pusher: Error during disconnect:', e);
        }
        pusherRef.current = null;
      }
    };
  }, [userId]); // Removed onMessage from dependencies
};


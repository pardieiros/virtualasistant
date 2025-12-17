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
    
    // Detect if we're using a proxy (domain name instead of localhost/IP)
    // When using a proxy (like Nginx Proxy Manager), the proxy handles the port redirection
    // so we must NOT include any port in the Pusher configuration to avoid URLs like wss://domain:6001
    // Instead, we let the browser use default ports (80 for ws, 443 for wss) which won't appear in the URL
    const useProxy = SOCKET_HOST !== 'localhost' && !SOCKET_HOST.match(/^\d+\.\d+\.\d+\.\d+$/);
    
    // Build base config
    const pusherConfig: any = {
      cluster: '',
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
      wsHost: SOCKET_HOST,
    };
    
    // Configure port based on whether we're using a proxy
    // When using a domain (proxy mode), do NOT set ports at all
    // This prevents Pusher from including :6001 in the URL (e.g., wss://domain:6001)
    // The browser will use default ports (80/443) which won't appear in the URL
    // The proxy (Nginx Proxy Manager) will handle routing to the actual Soketi server
    if (!useProxy) {
      // DIRECT CONNECTION MODE: Set port for direct connection to Soketi
      pusherConfig.wsPort = parseInt(SOCKET_PORT);
      pusherConfig.wssPort = parseInt(SOCKET_PORT);
    }
    // In proxy mode, we intentionally do NOT set wsPort/wssPort
    // This ensures Pusher uses default ports (80/443) without showing them in the URL
    
    // Log connection info (NEVER include port when using proxy - it confuses debugging)
    // We removed port from log when using proxy because the proxy handles port redirection
    // and including it in the log makes it seem like we're using a port when we're not
    const logInfo: any = {
      host: SOCKET_HOST,
      useTLS: SOCKET_USE_TLS,
      useProxy,
      authEndpoint,
      keyLength: SOCKET_KEY.length,
    };
    // Only include port in log for direct connections (not proxy)
    // IMPORTANT: Do NOT add port to log when useProxy is true - this was causing confusion
    if (!useProxy) {
      logInfo.port = SOCKET_PORT;
    }
    console.log('Pusher: Initializing connection', logInfo);
    
    const pusher = new Pusher(SOCKET_KEY, pusherConfig);

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


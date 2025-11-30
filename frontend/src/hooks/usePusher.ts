import { useEffect, useRef } from 'react';
import Pusher from 'pusher-js';

const SOCKET_HOST = import.meta.env.VITE_SOCKET_HOST || 'localhost';
const SOCKET_PORT = import.meta.env.VITE_SOCKET_PORT || '6001';
const SOCKET_KEY = import.meta.env.VITE_SOCKET_KEY || '';
const SOCKET_USE_TLS = import.meta.env.VITE_SOCKET_USE_TLS === 'true';

const scheme = SOCKET_USE_TLS ? 'https' : 'http';
const host = `${SOCKET_HOST}:${SOCKET_PORT}`;

export const usePusher = (userId: number | null, onMessage: (event: string, data: any) => void) => {
  const pusherRef = useRef<Pusher | null>(null);
  const channelRef = useRef<any>(null);

  useEffect(() => {
    if (!userId || !SOCKET_KEY) {
      return;
    }

    const pusher = new Pusher(SOCKET_KEY, {
      cluster: '',
      wsHost: SOCKET_HOST,
      wsPort: parseInt(SOCKET_PORT),
      wssPort: parseInt(SOCKET_PORT),
      enabledTransports: ['ws', 'wss'],
      forceTLS: SOCKET_USE_TLS,
    });

    pusherRef.current = pusher;

    const channelName = `private-user-${userId}`;
    const channel = pusher.subscribe(channelName);

    channel.bind('assistant-message', (data: any) => {
      onMessage('assistant-message', data);
    });

    channel.bind('shopping-updated', (data: any) => {
      onMessage('shopping-updated', data);
    });

    channel.bind('agenda-updated', (data: any) => {
      onMessage('agenda-updated', data);
    });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        channelRef.current.unbind_all();
        channelRef.current.unsubscribe();
      }
      if (pusherRef.current) {
        pusherRef.current.disconnect();
      }
    };
  }, [userId, onMessage]);
};


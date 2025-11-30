// This file will be processed by VitePWA injectManifest
// The workbox precaching will be injected automatically

// This will be replaced by workbox with the precache manifest
const manifest = self.__WB_MANIFEST;

// Service Worker for Push Notifications
self.addEventListener('push', (event) => {
  let data = {};
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { body: event.data.text() };
    }
  }

  const title = data.title || 'Personal Assistant';
  const body = data.body || 'You have a new notification';
  const icon = '/personal_assistance_logo.ico';
  const badge = '/personal_assistance_logo.ico';
  const data_payload = data.data || {};

  const options = {
    body: body,
    icon: icon,
    badge: badge,
    data: data_payload,
    vibrate: [200, 100, 200],
    tag: 'personal-assistant-notification',
    requireInteraction: false,
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const data = event.notification.data;
  
  // Handle different notification types
  if (data && data.type === 'agenda_event' && data.event_id) {
    // Navigate to agenda page
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
        // If a window is already open, focus it
        for (const client of clientList) {
          if (client.url.includes('/agenda') && 'focus' in client) {
            return client.focus();
          }
        }
        // Otherwise, open a new window
        if (clients.openWindow) {
          return clients.openWindow('/agenda');
        }
      })
    );
  } else {
    // Default: open the app
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
        for (const client of clientList) {
          if ('focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow('/');
        }
      })
    );
  }
});

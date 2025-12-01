import { pushSubscriptionAPI } from '../api/client';

export interface PushSubscriptionData {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

/**
 * Convert a base64 string to Uint8Array
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

/**
 * Get VAPID public key from backend
 */
async function getVapidPublicKey(): Promise<string> {
  try {
    const data = await pushSubscriptionAPI.getVapidPublicKey();
    return data.public_key;
  } catch (error) {
    console.error('Error fetching VAPID public key:', error);
    throw error;
  }
}

/**
 * Subscribe to push notifications
 */
export async function subscribeToPushNotifications(): Promise<PushSubscriptionData | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.warn('Push notifications are not supported in this browser');
    return null;
  }

  try {
    // Ensure service worker is registered and ready
    let registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      // Service worker not registered yet, register it
      registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      // Wait for it to be ready
      await navigator.serviceWorker.ready;
    } else {
      // Wait for existing registration to be ready
      await navigator.serviceWorker.ready;
    }
    
    // Get VAPID public key
    const vapidPublicKey = await getVapidPublicKey();
    if (!vapidPublicKey) {
      throw new Error('VAPID public key not available');
    }

    // Convert VAPID key from base64 URL-safe to Uint8Array
    // The key should be 65 bytes (0x04 prefix + 32 bytes X + 32 bytes Y)
    const keyArray = urlBase64ToUint8Array(vapidPublicKey);
    
    // Validate key length (should be 65 bytes for uncompressed P-256 public key)
    if (keyArray.length !== 65) {
      throw new Error(
        `Invalid VAPID public key length: expected 65 bytes, got ${keyArray.length}. ` +
        `Please regenerate VAPID keys using the updated script.`
      );
    }
    
    // Subscribe to push notifications
    // Create a new ArrayBuffer to ensure proper type compatibility
    const keyBuffer = new Uint8Array(keyArray).buffer;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBuffer,
    });

    // Convert subscription to format expected by backend
    const subscriptionData: PushSubscriptionData = {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: arrayBufferToBase64(subscription.getKey('p256dh')!),
        auth: arrayBufferToBase64(subscription.getKey('auth')!),
      },
    };

    // Register subscription with backend
    await pushSubscriptionAPI.register(subscriptionData);

    return subscriptionData;
  } catch (error) {
    console.error('Error subscribing to push notifications:', error);
    throw error;
  }
}

/**
 * Unsubscribe from push notifications
 */
export async function unsubscribeFromPushNotifications(endpoint: string): Promise<void> {
  try {
    // Ensure service worker is registered
    let registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      // Service worker not registered, nothing to unsubscribe
      return;
    }
    
    // Wait for it to be ready
    registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription && subscription.endpoint === endpoint) {
      await subscription.unsubscribe();
    }
    
    await pushSubscriptionAPI.unregister(endpoint);
  } catch (error) {
    console.error('Error unsubscribing from push notifications:', error);
    throw error;
  }
}

/**
 * Check if user is subscribed to push notifications
 */
export async function isSubscribedToPushNotifications(): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return false;
  }

  try {
    // Ensure service worker is registered
    let registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      // Service worker not registered yet
      return false;
    }
    
    // Wait for it to be ready
    registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    return subscription !== null;
  } catch (error) {
    console.error('Error checking push subscription:', error);
    return false;
  }
}

/**
 * Convert ArrayBuffer to base64 string
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}


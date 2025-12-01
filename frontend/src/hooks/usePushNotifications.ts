import { useState, useEffect, useCallback } from 'react'
import { pushSubscriptionAPI } from '../api/client'

export type PushNotificationStatus =
  | 'unsupported'
  | 'disabled'
  | 'enabled'
  | 'blocked'
  | 'loading'

interface PushSubscriptionData {
  endpoint: string
  keys: {
    p256dh: string
    auth: string
  }
}

interface UsePushNotificationsReturn {
  status: PushNotificationStatus
  isLoading: boolean
  error: string | null
  subscribe: () => Promise<void>
  unsubscribe: () => Promise<void>
  testNotification: () => Promise<void>
}

/**
 * Hook to manage Web Push Notifications
 * Handles subscription, unsubscription, and status management
 */
export function usePushNotifications(): UsePushNotificationsReturn {
  const [status, setStatus] = useState<PushNotificationStatus>('loading')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null)

  // Check feature support and current status
  useEffect(() => {
    const checkSupport = async () => {
      // Check if browser supports required APIs
      if (
        !('serviceWorker' in navigator) ||
        !('PushManager' in window) ||
        !('Notification' in window)
      ) {
        setStatus('unsupported')
        return
      }

      // Check notification permission
      if (Notification.permission === 'denied') {
        setStatus('blocked')
        return
      }

      if (Notification.permission === 'default') {
        setStatus('disabled')
        return
      }

      // Permission is granted, check if we have a subscription
      try {
        const reg = await navigator.serviceWorker.ready
        setRegistration(reg)

        const subscription = await reg.pushManager.getSubscription()
        if (subscription) {
          setStatus('enabled')
        } else {
          setStatus('disabled')
        }
      } catch (err) {
        console.error('Error checking push subscription:', err)
        setStatus('disabled')
      }
    }

    checkSupport()
  }, [])

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Check support
      if (
        !('serviceWorker' in navigator) ||
        !('PushManager' in window) ||
        !('Notification' in window)
      ) {
        throw new Error('Push notifications are not supported in this browser')
      }

      // Request notification permission
      const permission = await Notification.requestPermission()
      if (permission === 'denied') {
        setStatus('blocked')
        throw new Error('Notification permission was denied')
      }

      if (permission !== 'granted') {
        setStatus('disabled')
        throw new Error('Notification permission was not granted')
      }

      // Get or register service worker
      let reg = registration
      if (!reg) {
        reg = await navigator.serviceWorker.ready
        setRegistration(reg)
      }

      // Get VAPID public key from backend
      const vapidData = await pushSubscriptionAPI.getVapidPublicKey()
      const vapidPublicKey = vapidData.public_key

      if (!vapidPublicKey) {
        throw new Error('VAPID public key not received from server')
      }

      // Convert VAPID key from base64 URL-safe to Uint8Array
      // The key should be 65 bytes (0x04 prefix + 32 bytes X + 32 bytes Y)
      const keyArray = urlBase64ToUint8Array(vapidPublicKey)
      
      // Validate key length (should be 65 bytes for uncompressed P-256 public key)
      if (keyArray.length !== 65) {
        throw new Error(
          `Invalid VAPID public key length: expected 65 bytes, got ${keyArray.length}. ` +
          `Please regenerate VAPID keys using the updated script.`
        )
      }

      // Subscribe to push manager
      // Create a new ArrayBuffer to ensure proper type compatibility
      const keyBuffer = new Uint8Array(keyArray).buffer
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: keyBuffer,
      })

      // Extract subscription data
      const subscriptionData: PushSubscriptionData = {
        endpoint: subscription.endpoint,
        keys: {
          p256dh: arrayBufferToBase64(subscription.getKey('p256dh')!),
          auth: arrayBufferToBase64(subscription.getKey('auth')!),
        },
      }

      // Send subscription to backend
      await pushSubscriptionAPI.register(subscriptionData)

      setStatus('enabled')
    } catch (err: any) {
      console.error('Error subscribing to push notifications:', err)
      
      // Provide more helpful error messages
      let errorMessage = 'Failed to subscribe to push notifications'
      if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        errorMessage = 'Cannot connect to server. Please ensure the backend server is running and accessible.'
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      setStatus('disabled')
    } finally {
      setIsLoading(false)
    }
  }, [registration])

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      if (!registration) {
        const reg = await navigator.serviceWorker.ready
        setRegistration(reg)
      }

      const reg = registration || (await navigator.serviceWorker.ready)
      const subscription = await reg.pushManager.getSubscription()

      if (subscription) {
        // Unsubscribe from push manager
        await subscription.unsubscribe()

        // Notify backend
        await pushSubscriptionAPI.unregister(subscription.endpoint)

        setStatus('disabled')
      }
    } catch (err: any) {
      console.error('Error unsubscribing from push notifications:', err)
      setError(err.message || 'Failed to unsubscribe from push notifications')
    } finally {
      setIsLoading(false)
    }
  }, [registration])

  // Send test notification
  const testNotification = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await pushSubscriptionAPI.test()
      if (!result.success) {
        throw new Error(result.message || 'Failed to send test notification')
      }
    } catch (err: any) {
      console.error('Error sending test notification:', err)
      setError(err.message || 'Failed to send test notification')
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    status,
    isLoading,
    error,
    subscribe,
    unsubscribe,
    testNotification,
  }
}

/**
 * Convert base64 URL-safe string to Uint8Array
 * Required for VAPID public key
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

/**
 * Convert ArrayBuffer to base64 string
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return window.btoa(binary)
}


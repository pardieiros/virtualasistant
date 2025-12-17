import { useState, useEffect } from 'react';
import { subscribeToPushNotifications, isSubscribedToPushNotifications } from '../utils/pushNotifications';

interface NotificationPermissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const NotificationPermissionModal: React.FC<NotificationPermissionModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      checkSubscription();
    }
  }, [isOpen]);

  const checkSubscription = async () => {
    try {
      const subscribed = await isSubscribedToPushNotifications();
      setIsSubscribed(subscribed);
    } catch (error) {
      console.error('Error checking subscription:', error);
    }
  };

  const handleEnableNotifications = async () => {
    if (!('Notification' in window)) {
      setError('This browser does not support notifications');
      return;
    }

    if (!('serviceWorker' in navigator)) {
      setError('This browser does not support service workers');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Request notification permission
      const permission = await Notification.requestPermission();
      
      if (permission !== 'granted') {
        setError('Notification permission was denied. Please enable it in your browser settings.');
        return;
      }

      // Subscribe to push notifications
      await subscribeToPushNotifications();
      
      // Mark as dismissed in localStorage
      localStorage.setItem('notification_permission_dismissed', 'true');
      
      setIsSubscribed(true);
      onSuccess();
      
      // Close modal after a short delay
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error: any) {
      console.error('Error enabling notifications:', error);
      setError(error.message || 'Failed to enable notifications. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('notification_permission_dismissed', 'true');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-8">
      <div className="card max-w-md w-full">
        <h3 className="text-2xl font-bold text-primary-gold mb-4">
          Enable Push Notifications
        </h3>
        
        <p className="text-text-medium mb-6">
          Get notified about important events, agenda reminders, and shopping list updates. 
          We'll only send you notifications when something important happens.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-300 text-sm">
            {error}
          </div>
        )}

        {isSubscribed ? (
          <div className="mb-4 p-3 bg-green-500/20 border border-green-500/50 rounded text-green-300 text-sm">
            ✓ Notifications enabled successfully!
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              <button
                onClick={handleEnableNotifications}
                disabled={isLoading}
                className="btn-primary w-full"
              >
                {isLoading ? 'Enabling...' : 'Enable Notifications'}
              </button>
              
              <button
                onClick={handleDismiss}
                disabled={isLoading}
                className="btn-secondary w-full"
              >
                Not Now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationPermissionModal;





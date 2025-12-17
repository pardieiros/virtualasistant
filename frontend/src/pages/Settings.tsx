import { useState, useEffect } from 'react';
import { homeAssistantAPI, notificationPreferencesAPI, terminalAPI } from '../api/client';
import type { HomeAssistantConfig, UserNotificationPreferences, TerminalAPIConfig } from '../types';
import { usePushNotifications } from '../hooks/usePushNotifications';

const Settings = () => {
  const [haConfig, setHaConfig] = useState<HomeAssistantConfig | null>(null);
  const [, setNotifPreferences] = useState<UserNotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingNotif, setSavingNotif] = useState(false);
  
  // Use push notifications hook
  const { status, isLoading: pushLoading, error: pushError, subscribe, testNotification } = usePushNotifications();
  const [formData, setFormData] = useState({
    base_url: '',
    long_lived_token: '',
    enabled: false,
  });
  const [terminalFormData, setTerminalFormData] = useState({
    api_url: '',
    api_token: '',
    enabled: false,
  });
  const [terminalConfig, setTerminalConfig] = useState<TerminalAPIConfig | null>(null);
  const [savingTerminal, setSavingTerminal] = useState(false);
  const [notifFormData, setNotifFormData] = useState({
    agenda_events_enabled: true,
    agenda_reminder_minutes: 15,
    shopping_updates_enabled: false,
    notes_enabled: true,
  });

  useEffect(() => {
    loadConfig();
    loadNotificationPreferences();
    loadTerminalConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const config = await homeAssistantAPI.getConfig();
      if (config) {
        setHaConfig(config);
        setFormData({
          base_url: config.base_url || '',
          long_lived_token: '',
          enabled: config.enabled,
        });
      }
    } catch (error) {
      console.error('Error loading config:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadNotificationPreferences = async () => {
    try {
      const preferences = await notificationPreferencesAPI.getPreferences();
      if (preferences) {
        setNotifPreferences(preferences);
        setNotifFormData({
          agenda_events_enabled: preferences.agenda_events_enabled,
          agenda_reminder_minutes: preferences.agenda_reminder_minutes,
          shopping_updates_enabled: preferences.shopping_updates_enabled,
          notes_enabled: preferences.notes_enabled ?? true,
        });
      }
    } catch (error) {
      console.error('Error loading notification preferences:', error);
    }
  };

  const loadTerminalConfig = async () => {
    try {
      const config = await terminalAPI.getConfig();
      if (config) {
        setTerminalConfig(config);
        setTerminalFormData({
          api_url: config.api_url || '',
          api_token: '',
          enabled: config.enabled,
        });
      }
    } catch (error) {
      console.error('Error loading terminal config:', error);
    }
  };

  const handleSaveTerminal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingTerminal(true);
      const updated = await terminalAPI.updateConfig(terminalFormData);
      setTerminalConfig(updated);
      alert('Terminal API settings saved successfully!');
    } catch (error) {
      console.error('Error saving terminal config:', error);
      alert('Error saving Terminal API settings');
    } finally {
      setSavingTerminal(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      const updated = await homeAssistantAPI.updateConfig(formData);
      setHaConfig(updated);
      alert('Settings saved successfully!');
    } catch (error) {
      console.error('Error saving config:', error);
      alert('Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingNotif(true);
      const updated = await notificationPreferencesAPI.updatePreferences(notifFormData);
      setNotifPreferences(updated);
      alert('Notification preferences saved successfully!');
    } catch (error) {
      console.error('Error saving notification preferences:', error);
      alert('Error saving notification preferences');
    } finally {
      setSavingNotif(false);
    }
  };

  const handleEnableNotifications = async () => {
    try {
      await subscribe();
      alert('Notifications enabled successfully!');
    } catch (error: any) {
      console.error('Error enabling notifications:', error);
      alert(error.message || 'Failed to enable notifications. Please try again.');
    }
  };

  const handleTestNotification = async () => {
    try {
      // Ensure service worker is ready
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.ready;
        if (!registration) {
          throw new Error('Service worker is not ready');
        }
      }

      // Send test notification request to backend
      await testNotification();
      
      // Don't show alert - the notification will appear as a real push notification
      // The backend will send the push notification which will be handled by the service worker
      console.log('Test notification request sent. Check your device for the notification.');
    } catch (error: any) {
      console.error('Error testing notification:', error);
      const errorMessage = error.response?.data?.error || error.message || 'Error testing notification';
      alert(errorMessage);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center text-text-medium py-12">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold text-primary-gold mb-6">Settings</h2>

      <div className="card mb-6">
        <h3 className="text-xl font-semibold text-text-light mb-4">
          Home Assistant Integration
        </h3>
        <p className="text-text-medium mb-6">
          Configure your Home Assistant connection to enable smart home control through your assistant.
        </p>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-text-medium mb-2">Base URL</label>
            <input
              type="url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              className="input-field w-full"
              placeholder="http://homeassistant.local:8123"
            />
          </div>

          <div>
            <label className="block text-text-medium mb-2">Long-Lived Access Token</label>
            <input
              type="password"
              value={formData.long_lived_token}
              onChange={(e) => setFormData({ ...formData, long_lived_token: e.target.value })}
              className="input-field w-full"
              placeholder={haConfig?.token_configured ? '••••••••' : 'Enter your token'}
            />
            <p className="text-xs text-text-medium mt-1">
              {haConfig?.token_configured
                ? 'Token is already configured. Leave blank to keep current token, or enter a new one to update.'
                : 'Create a long-lived access token in your Home Assistant profile settings.'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="w-4 h-4"
            />
            <label className="text-text-medium">Enable Home Assistant integration</label>
          </div>

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </form>
      </div>

      <div className="card mb-6">
        <h3 className="text-xl font-semibold text-text-light mb-4">
          Push Notifications
        </h3>
        <p className="text-text-medium mb-6">
          Configure when and how you want to receive push notifications.
        </p>

        {/* Notification Status and Enable Button */}
        <div className="mb-6 p-4 bg-dark-warm-gray rounded-lg border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-light font-medium">Notification Status</span>
            {status === 'loading' ? (
              <span className="text-text-medium text-sm">Checking...</span>
            ) : status === 'enabled' ? (
              <span className="text-green-400 text-sm">✓ Enabled</span>
            ) : status === 'blocked' ? (
              <span className="text-red-400 text-sm">✗ Blocked</span>
            ) : status === 'unsupported' ? (
              <span className="text-red-400 text-sm">✗ Unsupported</span>
            ) : (
              <span className="text-red-400 text-sm">✗ Not Enabled</span>
            )}
          </div>
          {pushError && (
            <div className="mt-2 p-2 bg-red-900/20 border border-red-500/30 rounded text-sm text-red-400">
              {pushError}
            </div>
          )}
          {status === 'disabled' && (
            <div className="mt-3">
              <button
                onClick={handleEnableNotifications}
                disabled={pushLoading}
                className="btn-primary w-full"
              >
                {pushLoading ? 'Enabling...' : 'Enable Push Notifications'}
              </button>
              <p className="text-xs text-text-medium mt-2">
                Click to enable push notifications in your browser. You'll be asked to grant permission.
              </p>
            </div>
          )}
          {status === 'blocked' && (
            <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded text-sm text-yellow-400">
              Push notifications are blocked. Please enable them in your browser settings.
            </div>
          )}
          {status === 'unsupported' && (
            <div className="mt-3 p-3 bg-red-900/20 border border-red-500/30 rounded text-sm text-red-400">
              Your browser does not support push notifications.
            </div>
          )}
        </div>

        <form onSubmit={handleSaveNotifications} className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={notifFormData.agenda_events_enabled}
                onChange={(e) => setNotifFormData({ ...notifFormData, agenda_events_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-text-medium">Enable notifications for agenda events</label>
            </div>

            {notifFormData.agenda_events_enabled && (
              <div>
                <label className="block text-text-medium mb-2">
                  Reminder time (minutes before event)
                </label>
                <input
                  type="number"
                  min="1"
                  max="1440"
                  value={notifFormData.agenda_reminder_minutes}
                  onChange={(e) => setNotifFormData({ ...notifFormData, agenda_reminder_minutes: parseInt(e.target.value) || 15 })}
                  className="input-field w-full"
                />
                <p className="text-xs text-text-medium mt-1">
                  You'll receive a notification this many minutes before each event starts (if you enabled notifications for that event).
                </p>
              </div>
            )}

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={notifFormData.shopping_updates_enabled}
                onChange={(e) => setNotifFormData({ ...notifFormData, shopping_updates_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-text-medium">Enable notifications for shopping list updates</label>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={notifFormData.notes_enabled}
                onChange={(e) => setNotifFormData({ ...notifFormData, notes_enabled: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-text-medium">Enable notifications for notes</label>
            </div>
          </div>

          <button type="submit" disabled={savingNotif} className="btn-primary">
            {savingNotif ? 'Saving...' : 'Save Notification Preferences'}
          </button>

          {status === 'enabled' && (
            <div className="mt-4 pt-4 border-t border-border">
              <button 
                type="button" 
                onClick={handleTestNotification} 
                disabled={pushLoading}
                className="btn-secondary"
              >
                {pushLoading ? 'Sending...' : 'Test Push Notification'}
              </button>
              <p className="text-xs text-text-medium mt-2">
                Send a test notification to verify that push notifications are working correctly. 
                The notification will appear on your device even with the screen locked.
              </p>
            </div>
          )}
        </form>
      </div>

      <div className="card mb-6">
        <h3 className="text-xl font-semibold text-text-light mb-4">
          Terminal API Integration (Proxmox)
        </h3>
        <p className="text-text-medium mb-6">
          Configure the Terminal API connection to enable Proxmox host management through your assistant.
          You can ask things like "Vê se os containers estão a correr" or "Mostra-me os logs do searxng".
        </p>

        <form onSubmit={handleSaveTerminal} className="space-y-4">
          <div>
            <label className="block text-text-medium mb-2">API URL</label>
            <input
              type="url"
              value={terminalFormData.api_url}
              onChange={(e) => setTerminalFormData({ ...terminalFormData, api_url: e.target.value })}
              className="input-field w-full"
              placeholder="http://192.168.1.73:8900"
            />
            <p className="text-xs text-text-medium mt-1">
              URL of the Terminal API service running on your Proxmox host.
            </p>
          </div>

          <div>
            <label className="block text-text-medium mb-2">API Token</label>
            <input
              type="password"
              value={terminalFormData.api_token}
              onChange={(e) => setTerminalFormData({ ...terminalFormData, api_token: e.target.value })}
              className="input-field w-full"
              placeholder={terminalConfig?.token_configured ? '••••••••' : 'Enter your token'}
            />
            <p className="text-xs text-text-medium mt-1">
              {terminalConfig?.token_configured
                ? 'Token is already configured. Leave blank to keep current token, or enter a new one to update.'
                : 'Bearer token for Terminal API authentication. Generate a strong token on the Proxmox host.'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={terminalFormData.enabled}
              onChange={(e) => setTerminalFormData({ ...terminalFormData, enabled: e.target.checked })}
              className="w-4 h-4"
            />
            <label className="text-text-medium">Enable Terminal API integration</label>
          </div>

          <button type="submit" disabled={savingTerminal} className="btn-primary">
            {savingTerminal ? 'Saving...' : 'Save Terminal API Settings'}
          </button>
        </form>
      </div>

      <div className="card">
        <h3 className="text-xl font-semibold text-text-light mb-4">About</h3>
        <div className="text-text-medium space-y-2">
          <p>Personal Assistant v0.1.0</p>
          <p>Built with Django, React, and Ollama</p>
        </div>
      </div>

    </div>
  );
};

export default Settings;


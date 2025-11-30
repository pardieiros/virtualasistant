import { useState, useEffect } from 'react';
import { homeAssistantAPI } from '../api/client';
import type { HomeAssistantConfig } from '../types';

const Settings = () => {
  const [haConfig, setHaConfig] = useState<HomeAssistantConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    base_url: '',
    long_lived_token: '',
    enabled: false,
  });

  useEffect(() => {
    loadConfig();
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


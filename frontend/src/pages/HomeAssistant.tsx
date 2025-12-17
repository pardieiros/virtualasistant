import { useState, useEffect } from 'react';
import { homeAssistantAPI } from '../api/client';

interface Device {
  entity_id: string;
  name: string;
  alias: string | null;
  area: string;
  domain: string;
  state: string;
  attributes: any;
}

interface Area {
  id: string;
  name: string;
  devices: Device[];
}

const HomeAssistant = () => {
  const [areas, setAreas] = useState<Area[]>([]);
  const [noAreaDevices, setNoAreaDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingAlias, setEditingAlias] = useState<{ entityId: string; alias: string; area: string } | null>(null);
  const [newAlias, setNewAlias] = useState({ alias: '', area: '' });

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      setLoading(true);
      const data = await homeAssistantAPI.getAreasAndDevices();
      setAreas(data.areas || []);
      setNoAreaDevices(data.no_area_devices || []);
    } catch (error) {
      console.error('Error loading devices:', error);
      alert('Error loading Home Assistant devices');
    } finally {
      setLoading(false);
    }
  };

  const handleControlDevice = async (device: Device, action: string) => {
    try {
      const domain = device.domain;
      let service = '';
      let serviceData: any = { entity_id: device.entity_id };

      if (action === 'turn_on') {
        service = 'turn_on';
        if (domain === 'climate') {
          // For climate, we might want to set temperature
          serviceData.hvac_mode = 'heat';
        }
      } else if (action === 'turn_off') {
        service = 'turn_off';
      } else if (action === 'toggle') {
        service = 'toggle';
      }

      await homeAssistantAPI.controlDevice(device.entity_id, domain, service, serviceData);
      // Reload devices to get updated states
      setTimeout(() => loadDevices(), 500);
    } catch (error) {
      console.error('Error controlling device:', error);
      alert('Error controlling device');
    }
  };

  const handleSetTemperature = async (device: Device, temperature: number) => {
    try {
      await homeAssistantAPI.controlDevice(device.entity_id, device.domain, 'set_temperature', {
        entity_id: device.entity_id,
        temperature: temperature,
      });
      setTimeout(() => loadDevices(), 500);
    } catch (error) {
      console.error('Error setting temperature:', error);
      alert('Error setting temperature');
    }
  };

  const handleSaveAlias = async (device: Device) => {
    try {
      if (!newAlias.alias.trim()) {
        alert('Please enter an alias name');
        return;
      }

      // Check if alias already exists for this entity
      const aliases = await homeAssistantAPI.getDeviceAliases();
      const existingAlias = aliases.find((a: any) => a.entity_id === device.entity_id);

      if (existingAlias) {
        await homeAssistantAPI.updateDeviceAlias(existingAlias.id, {
          alias: newAlias.alias,
          area: newAlias.area || device.area,
        });
      } else {
        await homeAssistantAPI.createDeviceAlias({
          entity_id: device.entity_id,
          alias: newAlias.alias,
          area: newAlias.area || device.area,
        });
      }

      setEditingAlias(null);
      setNewAlias({ alias: '', area: '' });
      await loadDevices();
    } catch (error) {
      console.error('Error saving alias:', error);
      alert('Error saving alias');
    }
  };

  const handleDeleteAlias = async (device: Device) => {
    try {
      const aliases = await homeAssistantAPI.getDeviceAliases();
      const existingAlias = aliases.find((a: any) => a.entity_id === device.entity_id);
      
      if (existingAlias) {
        if (confirm(`Delete alias "${existingAlias.alias}"?`)) {
          await homeAssistantAPI.deleteDeviceAlias(existingAlias.id);
          await loadDevices();
        }
      }
    } catch (error) {
      console.error('Error deleting alias:', error);
      alert('Error deleting alias');
    }
  };

  const renderDevice = (device: Device) => {
    const displayName = device.alias || device.name;
    const isOn = device.state === 'on' || device.state === 'heat' || device.state === 'cool';
    const canControl = ['light', 'switch', 'climate', 'fan'].includes(device.domain);

    return (
      <div key={device.entity_id} className="card mb-3 p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-text-light">{displayName}</h4>
            <p className="text-sm text-text-medium">
              {device.entity_id} • {device.domain} • State: {device.state}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {canControl && (
              <>
                {device.domain === 'climate' ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="16"
                      max="30"
                      value={device.attributes?.temperature || 20}
                      onChange={(e) => {
                        const temp = parseInt(e.target.value);
                        if (temp >= 16 && temp <= 30) {
                          handleSetTemperature(device, temp);
                        }
                      }}
                      className="input-field w-20 text-center"
                    />
                    <span className="text-text-medium">°C</span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleControlDevice(device, isOn ? 'turn_off' : 'turn_on')}
                    className={`btn-primary ${isOn ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'}`}
                  >
                    {isOn ? 'ON' : 'OFF'}
                  </button>
                )}
              </>
            )}
            {device.alias ? (
              <button
                onClick={() => handleDeleteAlias(device)}
                className="btn-secondary text-sm"
                title="Delete alias"
              >
                🗑️
              </button>
            ) : (
              <button
                onClick={() => {
                  setEditingAlias({ entityId: device.entity_id, alias: '', area: device.area });
                  setNewAlias({ alias: '', area: device.area });
                }}
                className="btn-secondary text-sm"
                title="Add alias"
              >
                ✏️
              </button>
            )}
          </div>
        </div>
        {editingAlias?.entityId === device.entity_id && (
          <div className="mt-3 p-3 bg-dark-warm-gray rounded-lg">
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Alias name (e.g., 'ar condicionado da cozinha')"
                value={newAlias.alias}
                onChange={(e) => setNewAlias({ ...newAlias, alias: e.target.value })}
                className="input-field w-full"
              />
              <input
                type="text"
                placeholder="Area (e.g., 'Cozinha')"
                value={newAlias.area}
                onChange={(e) => setNewAlias({ ...newAlias, area: e.target.value })}
                className="input-field w-full"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleSaveAlias(device)}
                  className="btn-primary flex-1"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditingAlias(null);
                    setNewAlias({ alias: '', area: '' });
                  }}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center text-text-medium py-12">Loading Home Assistant devices...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-primary-gold">Home Assistant</h2>
        <button onClick={loadDevices} className="btn-secondary">
          🔄 Refresh
        </button>
      </div>

      {areas.length === 0 && noAreaDevices.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-text-medium">No devices found. Make sure Home Assistant is configured and running.</p>
        </div>
      )}

      {areas.map((area) => (
        <div key={area.id || area.name} className="mb-6">
          <h3 className="text-xl font-semibold text-text-light mb-4 flex items-center gap-2">
            🏠 {area.name}
          </h3>
          {area.devices.length === 0 ? (
            <p className="text-text-medium text-sm ml-4">No devices in this area</p>
          ) : (
            <div className="space-y-2">
              {area.devices.map(renderDevice)}
            </div>
          )}
        </div>
      ))}

      {noAreaDevices.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-text-light mb-4">Other Devices</h3>
          <div className="space-y-2">
            {noAreaDevices.map(renderDevice)}
          </div>
        </div>
      )}
    </div>
  );
};

export default HomeAssistant;




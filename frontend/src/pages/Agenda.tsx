import { useState, useEffect } from 'react';
import { agendaAPI } from '../api/client';
import type { AgendaEvent } from '../types';
import { format, parseISO } from 'date-fns';

const Agenda = () => {
  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_datetime: '',
    end_datetime: '',
    location: '',
    category: 'personal' as 'personal' | 'work' | 'health' | 'other',
    all_day: false,
  });

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const now = new Date();
      const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      
      const data = await agendaAPI.list({
        start_date: startOfMonth.toISOString(),
        end_date: endOfMonth.toISOString(),
      });
      setEvents(data);
    } catch (error) {
      console.error('Error loading events:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await agendaAPI.create(formData);
      setShowForm(false);
      setFormData({
        title: '',
        description: '',
        start_datetime: '',
        end_datetime: '',
        location: '',
        category: 'personal',
        all_day: false,
      });
      loadEvents();
    } catch (error) {
      console.error('Error creating event:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this event?')) return;
    try {
      await agendaAPI.delete(id);
      loadEvents();
    } catch (error) {
      console.error('Error deleting event:', error);
    }
  };

  const categoryColors = {
    personal: 'bg-primary-gold/20 text-primary-gold border-primary-gold/50',
    work: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
    health: 'bg-status-success/20 text-status-success border-status-success/50',
    other: 'bg-text-medium/20 text-text-medium border-text-medium/50',
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-primary-gold">Agenda</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          + Add Event
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-text-medium mb-2">Title *</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="input-field w-full"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2">Start Date & Time *</label>
                <input
                  type="datetime-local"
                  value={formData.start_datetime}
                  onChange={(e) => setFormData({ ...formData, start_datetime: e.target.value })}
                  className="input-field w-full"
                  required
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2">End Date & Time</label>
                <input
                  type="datetime-local"
                  value={formData.end_datetime}
                  onChange={(e) => setFormData({ ...formData, end_datetime: e.target.value })}
                  className="input-field w-full"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-text-medium mb-2">Location</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-text-medium mb-2">Category</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value as any })}
                  className="input-field w-full"
                >
                  <option value="personal">Personal</option>
                  <option value="work">Work</option>
                  <option value="health">Health</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-text-medium mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="input-field w-full"
                rows={3}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.all_day}
                onChange={(e) => setFormData({ ...formData, all_day: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-text-medium">All day event</label>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary">
                Add Event
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center text-text-medium py-12">Loading...</div>
      ) : events.length === 0 ? (
        <div className="text-center text-text-medium py-12">
          No events found. Add your first event!
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => {
            const startDate = parseISO(event.start_datetime);
            const endDate = event.end_datetime ? parseISO(event.end_datetime) : null;
            
            return (
              <div
                key={event.id}
                className={`card border-l-4 ${categoryColors[event.category]}`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-text-light mb-2">
                      {event.title}
                    </h3>
                    <div className="space-y-1 text-text-medium">
                      <div className="flex items-center gap-2">
                        <span>📅</span>
                        <span>
                          {format(startDate, 'MMM d, yyyy')} at{' '}
                          {format(startDate, 'HH:mm')}
                          {endDate && ` - ${format(endDate, 'HH:mm')}`}
                        </span>
                      </div>
                      {event.location && (
                        <div className="flex items-center gap-2">
                          <span>📍</span>
                          <span>{event.location}</span>
                        </div>
                      )}
                      {event.description && (
                        <p className="mt-2">{event.description}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(event.id)}
                    className="text-status-error hover:text-status-error/80 ml-4"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Agenda;


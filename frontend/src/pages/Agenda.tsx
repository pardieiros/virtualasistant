import { useState, useEffect, useMemo } from 'react';
import { agendaAPI } from '../api/client';
import type { AgendaEvent } from '../types';
import { format, parseISO, startOfDay, endOfDay, isSameDay, isPast, startOfMonth, endOfMonth, eachDayOfInterval, getDay, isSameMonth, addMonths, subMonths, addDays, subDays } from 'date-fns';
import { subscribeToPushNotifications, isSubscribedToPushNotifications } from '../utils/pushNotifications';

const Agenda = () => {
  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>(startOfDay(new Date()));
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [activeTab, setActiveTab] = useState<'upcoming' | 'past'>('upcoming');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_datetime: '',
    end_datetime: '',
    location: '',
    category: 'personal' as 'personal' | 'work' | 'health' | 'other',
    all_day: false,
    send_notification: false,
  });

  useEffect(() => {
    loadEvents();
    // Request push notification permission and subscribe
    requestPushNotificationPermission();
  }, []);

  const requestPushNotificationPermission = async () => {
    try {
      const isSubscribed = await isSubscribedToPushNotifications();
      if (!isSubscribed) {
        // Request permission
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          await subscribeToPushNotifications();
        }
      }
    } catch (error) {
      console.error('Error setting up push notifications:', error);
    }
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      // Load all events
      const data = await agendaAPI.list();
      setEvents(data);
    } catch (error) {
      console.error('Error loading events:', error);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const filteredEvents = useMemo(() => {
    const now = new Date();
    if (activeTab === 'upcoming') {
      // Show only events for selected date (including today and future)
      return events.filter(event => {
        const eventDate = parseISO(event.start_datetime);
        return isSameDay(eventDate, selectedDate);
      });
    } else {
      // Show only past events (excluding today)
      return events.filter(event => {
        const eventDate = parseISO(event.start_datetime);
        return isPast(eventDate) && !isSameDay(eventDate, startOfDay(now));
      });
    }
  }, [events, selectedDate, activeTab]);

  const eventsByDate = useMemo(() => {
    const grouped: { [key: string]: AgendaEvent[] } = {};
    filteredEvents.forEach(event => {
      const eventDate = format(parseISO(event.start_datetime), 'yyyy-MM-dd');
      if (!grouped[eventDate]) {
        grouped[eventDate] = [];
      }
      grouped[eventDate].push(event);
    });
    return grouped;
  }, [filteredEvents]);

  const calendarDays = useMemo(() => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const calendarStart = startOfDay(subDays(monthStart, getDay(monthStart)));
    const calendarEnd = endOfDay(addDays(monthEnd, 6 - getDay(monthEnd)));
    return eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  }, [currentMonth]);

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
        send_notification: false,
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

  const handleDateSelect = (date: Date) => {
    setSelectedDate(startOfDay(date));
    setActiveTab('upcoming');
  };

  const getEventsForDate = (date: Date) => {
    return events.filter(event => {
      const eventDate = parseISO(event.start_datetime);
      return isSameDay(eventDate, date);
    });
  };

  const categoryColors = {
    personal: 'bg-primary-gold/20 text-primary-gold border-primary-gold/50',
    work: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
    health: 'bg-status-success/20 text-status-success border-status-success/50',
    other: 'bg-text-medium/20 text-text-medium border-text-medium/50',
  };

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-primary-gold">Agenda</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary text-sm sm:text-base">
          + Add Event
        </button>
        </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-primary-gold/20">
        <button
          onClick={() => setActiveTab('upcoming')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'upcoming'
              ? 'text-primary-gold border-b-2 border-primary-gold'
              : 'text-text-medium hover:text-text-light'
          }`}
        >
          Upcoming
        </button>
        <button
          onClick={() => setActiveTab('past')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'past'
              ? 'text-primary-gold border-b-2 border-primary-gold'
              : 'text-text-medium hover:text-text-light'
          }`}
        >
          Past
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
            <div className="space-y-2">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.all_day}
                onChange={(e) => setFormData({ ...formData, all_day: e.target.checked })}
                className="w-4 h-4"
              />
              <label className="text-text-medium">All day event</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.send_notification}
                  onChange={(e) => setFormData({ ...formData, send_notification: e.target.checked })}
                  className="w-4 h-4"
                />
                <label className="text-text-medium">Send push notification reminder</label>
              </div>
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

      {activeTab === 'upcoming' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="lg:col-span-1">
            <div className="card">
              {/* Calendar Header */}
              <div className="flex items-center justify-between mb-4">
                <button
                  onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                  className="btn-secondary p-2 text-sm"
                >
                  ←
                </button>
                <h3 className="text-lg font-semibold text-text-light">
                  {format(currentMonth, 'MMMM yyyy')}
                </h3>
                <button
                  onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                  className="btn-secondary p-2 text-sm"
                >
                  →
                </button>
              </div>

              {/* Week Days Header */}
              <div className="grid grid-cols-7 gap-1 mb-2">
                {weekDays.map(day => (
                  <div key={day} className="text-center text-xs font-semibold text-text-medium py-2">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar Days */}
              <div className="grid grid-cols-7 gap-1">
                {calendarDays.map((day, idx) => {
                  const dayEvents = getEventsForDate(day);
                  const isCurrentMonth = isSameMonth(day, currentMonth);
                  const isSelected = isSameDay(day, selectedDate);
                  const isToday = isSameDay(day, new Date());
                  const isPastDate = isPast(day) && !isToday;

                  return (
                    <button
                      key={idx}
                      onClick={() => handleDateSelect(day)}
                      disabled={isPastDate}
                      className={`
                        aspect-square p-1 sm:p-2 rounded-lg text-xs sm:text-sm transition-colors
                        ${!isCurrentMonth ? 'text-text-medium/30' : 'text-text-light'}
                        ${isSelected ? 'bg-primary-gold text-dark-charcoal font-bold' : ''}
                        ${!isSelected && isCurrentMonth && !isPastDate ? 'hover:bg-dark-warm-gray' : ''}
                        ${isToday && !isSelected ? 'ring-2 ring-primary-gold/50' : ''}
                        ${isPastDate ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                        ${dayEvents.length > 0 ? 'relative' : ''}
                      `}
                    >
                      {format(day, 'd')}
                      {dayEvents.length > 0 && (
                        <span className="absolute bottom-0.5 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-primary-gold rounded-full"></span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Events for Selected Date */}
          <div className="lg:col-span-2">
            <div className="mb-4">
              <h3 className="text-xl font-semibold text-text-light">
                {format(selectedDate, 'EEEE, MMMM d, yyyy')}
              </h3>
            </div>

      {loading ? (
        <div className="text-center text-text-medium py-12">Loading...</div>
            ) : filteredEvents.length === 0 ? (
        <div className="text-center text-text-medium py-12">
                <p>No events for this date.</p>
                <p className="text-sm mt-2">Add an event using the button above!</p>
        </div>
      ) : (
              <div className="space-y-3">
                {filteredEvents
                  .sort((a, b) => parseISO(a.start_datetime).getTime() - parseISO(b.start_datetime).getTime())
                  .map((event) => {
            const startDate = parseISO(event.start_datetime);
            const endDate = event.end_datetime ? parseISO(event.end_datetime) : null;
            
            return (
              <div
                key={event.id}
                className={`card border-l-4 ${categoryColors[event.category]}`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                            <h3 className="text-lg sm:text-xl font-semibold text-text-light mb-2">
                      {event.title}
                    </h3>
                            <div className="space-y-1 text-text-medium text-sm">
                      <div className="flex items-center gap-2">
                        <span>📅</span>
                        <span>
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
        </div>
      ) : (
        /* Past Events Tab */
        <div>
          {loading ? (
            <div className="text-center text-text-medium py-12">Loading...</div>
          ) : filteredEvents.length === 0 ? (
            <div className="text-center text-text-medium py-12">
              <p>No past events.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(eventsByDate)
                .sort(([dateA], [dateB]) => new Date(dateB).getTime() - new Date(dateA).getTime())
                .map(([dateStr, dateEvents]) => (
                  <div key={dateStr}>
                    <h3 className="text-lg font-semibold text-text-light mb-3">
                      {format(parseISO(dateStr), 'EEEE, MMMM d, yyyy')}
                    </h3>
                    <div className="space-y-3">
                      {dateEvents
                        .sort((a, b) => parseISO(a.start_datetime).getTime() - parseISO(b.start_datetime).getTime())
                        .map((event) => {
                          const startDate = parseISO(event.start_datetime);
                          const endDate = event.end_datetime ? parseISO(event.end_datetime) : null;
                          
                          return (
                            <div
                              key={event.id}
                              className={`card border-l-4 opacity-75 ${categoryColors[event.category]}`}
                            >
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <h3 className="text-lg sm:text-xl font-semibold text-text-light mb-2">
                                    {event.title}
                                  </h3>
                                  <div className="space-y-1 text-text-medium text-sm">
                                    <div className="flex items-center gap-2">
                                      <span>📅</span>
                                      <span>
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
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Agenda;


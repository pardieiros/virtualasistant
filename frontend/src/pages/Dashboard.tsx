import { useState, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationPermissionModal from '../components/NotificationPermissionModal';
import { isSubscribedToPushNotifications } from '../utils/pushNotifications';
import { homeAssistantAPI } from '../api/client';

const Dashboard = () => {
  const { logout } = useAuth();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [showNotificationModal, setShowNotificationModal] = useState(false);
  const [haEnabled, setHaEnabled] = useState(false);

  useEffect(() => {
    // Check if we should show the notification permission modal
    const checkNotificationPermission = async () => {
      // Check if user has already dismissed the modal
      const dismissed = localStorage.getItem('notification_permission_dismissed');
      if (dismissed === 'true') {
        return;
      }

      // Check if browser supports notifications
      if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        return;
      }

      // Check if user is already subscribed
      try {
        const isSubscribed = await isSubscribedToPushNotifications();
        if (!isSubscribed) {
          // Show modal after a short delay
          setTimeout(() => {
            setShowNotificationModal(true);
          }, 2000);
        }
      } catch (error) {
        console.error('Error checking notification subscription:', error);
      }
    };

    checkNotificationPermission();
  }, []);

  useEffect(() => {
    const checkHAConfig = async () => {
      try {
        const config = await homeAssistantAPI.getConfig();
        setHaEnabled(config?.enabled || false);
      } catch (error) {
        console.error('Error checking HA config:', error);
      }
    };
    checkHAConfig();
  }, []);

  const navItems = [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/actions', label: 'Quick Actions', icon: '⚡' },
    { path: '/conversation', label: 'Conversa', icon: '📞' },
    { path: '/shopping', label: 'Shopping', icon: '🛒' },
    { path: '/agenda', label: 'Agenda', icon: '📅' },
    { path: '/notes', label: 'Notes', icon: '📝' },
    { path: '/todo', label: 'To Do', icon: '✅' },
    { type: 'separator' },
    { path: '/video', label: 'Video Transcription', icon: '🎬' },
    ...(haEnabled ? [{ path: '/homeassistant', label: 'Home', icon: '🏠' }] : []),
    { type: 'separator' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-dark-charcoal flex flex-col">
      {/* Header */}
      <header className="bg-gradient-to-r from-dark-warm-gray via-dark-warm-gray to-dark-charcoal border-b border-primary-gold/20 shadow-lg">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img 
              src="/personal_assistance_logo_nobg.png" 
              alt="Personal Assistant Logo" 
              className="h-10 w-10 object-contain drop-shadow-lg"
            />
            <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-primary-gold to-primary-gold-soft bg-clip-text text-transparent">
              Personal Assistant
            </h1>
          </div>
          <button
            onClick={logout}
            className="btn-secondary text-sm hover:bg-primary-gold/10 hover:text-primary-gold transition-all"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex-1 flex relative">
        {/* Sidebar Toggle Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute left-2 top-2 z-50 lg:hidden bg-dark-warm-gray hover:bg-dark-warm-gray/80 text-text-light p-2 rounded-lg transition-colors"
          aria-label="Toggle sidebar"
        >
          {sidebarCollapsed ? '☰' : '✕'}
        </button>

        {/* Sidebar Navigation */}
        <nav
          className={`${
            sidebarCollapsed ? 'w-16' : 'w-64'
          } bg-dark-warm-gray border-r border-dark-warm-gray p-4 transition-all duration-300 ease-in-out hidden lg:block`}
        >
          <div className="flex justify-end mb-4">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-text-medium hover:text-text-light transition-colors"
              aria-label="Toggle sidebar"
            >
              {sidebarCollapsed ? '→' : '←'}
            </button>
          </div>
          <ul className="space-y-2">
            {navItems.map((item, index) => {
              if (item.type === 'separator') {
                return (
                  <li key={`separator-${index}`} className="my-2">
                    <div className="h-px bg-primary-gold/20 mx-4"></div>
                  </li>
                );
              }
              if (!item.path) return null;
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      sidebarCollapsed ? 'justify-center' : ''
                    } ${
                      isActive
                        ? 'bg-primary-gold text-dark-charcoal font-semibold'
                        : 'text-text-medium hover:bg-primary-gold/10 hover:text-primary-gold'
                    }`}
                    title={sidebarCollapsed ? item.label : ''}
                  >
                    <span className="text-xl">{item.icon}</span>
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Mobile Sidebar */}
        {!sidebarCollapsed && (
          <div className="lg:hidden fixed inset-0 z-40">
            <div
              className="fixed inset-0 bg-dark-charcoal/50"
              onClick={() => setSidebarCollapsed(true)}
            />
            <nav className="fixed left-0 top-0 bottom-0 w-64 bg-dark-warm-gray border-r border-dark-warm-gray p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-primary-gold font-semibold">Menu</h2>
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className="text-text-medium hover:text-text-light"
                >
                  ✕
                </button>
              </div>
              <ul className="space-y-2">
                {navItems.map((item, index) => {
                  if (item.type === 'separator') {
                    return (
                      <li key={`separator-${index}`} className="my-2">
                        <div className="h-px bg-primary-gold/20 mx-4"></div>
                      </li>
                    );
                  }
                  if (!item.path) return null;
                  const isActive = location.pathname === item.path;
                  return (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        onClick={() => setSidebarCollapsed(true)}
                        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                          isActive
                            ? 'bg-primary-gold text-dark-charcoal font-semibold'
                            : 'text-text-medium hover:bg-primary-gold/10 hover:text-primary-gold'
                        }`}
                      >
                        <span className="text-xl">{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      {/* Notification Permission Modal */}
      <NotificationPermissionModal
        isOpen={showNotificationModal}
        onClose={() => setShowNotificationModal(false)}
        onSuccess={() => {
          setShowNotificationModal(false);
        }}
      />
    </div>
  );
};

export default Dashboard;


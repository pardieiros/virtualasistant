import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/shopping', label: 'Shopping', icon: '🛒' },
    { path: '/agenda', label: 'Agenda', icon: '📅' },
    { path: '/notes', label: 'Notes', icon: '📝' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="min-h-screen bg-dark-charcoal flex flex-col">
      {/* Header */}
      <header className="bg-dark-warm-gray border-b border-dark-warm-gray">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img 
              src="/personal_assistance_logo_nobg.png" 
              alt="Personal Assistant Logo" 
              className="h-10 w-10 object-contain"
            />
            <h1 className="text-2xl font-bold text-primary-gold">Personal Assistant</h1>
          </div>
          <button
            onClick={logout}
            className="btn-secondary text-sm"
          >
            Logout
          </button>
        </div>
      </header>

      <div className="flex-1 flex">
        {/* Sidebar Navigation */}
        <nav className="w-64 bg-dark-warm-gray border-r border-dark-warm-gray p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-primary-gold text-dark-charcoal font-semibold'
                        : 'text-text-medium hover:bg-dark-warm-gray/80 hover:text-text-light'
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

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Dashboard;


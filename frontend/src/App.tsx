import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import ShoppingList from './pages/ShoppingList';
import Agenda from './pages/Agenda';
import Notes from './pages/Notes';
import TodoList from './pages/TodoList';
import Settings from './pages/Settings';
import HomeAssistant from './pages/HomeAssistant';
import Conversation from './pages/Conversation';
import VideoTranscription from './pages/VideoTranscription';
import QuickActions from './pages/QuickActions';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-dark-charcoal flex items-center justify-center">
        <div className="text-primary-gold text-xl">Loading...</div>
      </div>
    );
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          >
            <Route index element={<Chat />} />
            <Route path="actions" element={<QuickActions />} />
            <Route path="shopping" element={<ShoppingList />} />
            <Route path="agenda" element={<Agenda />} />
            <Route path="notes" element={<Notes />} />
            <Route path="todo" element={<TodoList />} />
            <Route path="conversation" element={<Conversation />} />
            <Route path="homeassistant" element={<HomeAssistant />} />
            <Route path="video" element={<VideoTranscription />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;


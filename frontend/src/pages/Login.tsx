import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-charcoal flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <img 
            src="/personal_assistance_logo_nobg.png" 
            alt="Personal Assistant Logo" 
            className="h-20 w-20 object-contain mx-auto mb-4"
          />
          <h1 className="text-4xl font-bold text-primary-gold mb-2">Personal Assistant</h1>
          <p className="text-text-medium">Your AI-powered assistant</p>
        </div>
        
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-status-error/20 border border-status-error text-status-error px-4 py-3 rounded-lg">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-text-medium mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field w-full"
                required
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-text-medium mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field w-full"
                required
                autoComplete="current-password"
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full disabled:opacity-50"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;


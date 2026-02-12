cat > app/page.tsx << 'EOF'
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [organization, setOrganization] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email, password }
        : { email, password, full_name: fullName, phone, organization };
      const { data } = await api.post(endpoint, payload);
      localStorage.setItem('token', data.access_token);
      router.push('/dashboard');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-3xl font-light mb-2 flex items-center gap-2">
        <i className="fas fa-shield-halbed"></i> VPN Pro
      </h1>
      <p className="text-sm opacity-70 mb-8">Minimal. Secure. Glass.</p>

      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setIsLogin(true)}
          className={`btn flex-1 ${isLogin ? 'btn-primary' : ''}`}
        >
          Login
        </button>
        <button
          onClick={() => setIsLogin(false)}
          className={`btn flex-1 ${!isLogin ? 'btn-primary' : ''}`}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs opacity-70 mb-1">Email</label>
          <input
            type="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-xs opacity-70 mb-1">Password</label>
          <input
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {!isLogin && (
          <>
            <div>
              <label className="block text-xs opacity-70 mb-1">Full Name</label>
              <input
                type="text"
                className="input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs opacity-70 mb-1">Phone</label>
              <input
                type="text"
                className="input"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs opacity-70 mb-1">Organization</label>
              <input
                type="text"
                className="input"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                required
              />
            </div>
          </>
        )}
        <button type="submit" disabled={loading} className="btn btn-primary w-full mt-6">
          {loading ? 'Processing...' : isLogin ? 'Login' : 'Register'}
        </button>
      </form>
    </div>
  );
}
EOF

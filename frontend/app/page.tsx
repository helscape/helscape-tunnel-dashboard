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
  const [errors, setErrors] = useState<Record<string, string>>({});
  const router = useRouter();

  const validateEmail = (email: string) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validatePassword = (pass: string) => {
    if (pass.length < 8) return 'Minimum 8 characters';
    if (!/\d/.test(pass)) return 'Must contain at least one number';
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(pass)) return 'Must contain at least one special character';
    return '';
  };

  const validatePhone = (phone: string) => {
    const re = /^[0-9]{10,13}$/;
    return re.test(phone) ? '' : 'Must be 10-13 digits';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // ---------- Client-side validation ----------
    if (!validateEmail(email)) {
      setErrors({ email: 'Invalid email format' });
      return;
    }

    if (!isLogin) {
      const pwdError = validatePassword(password);
      if (pwdError) {
        setErrors({ password: pwdError });
        return;
      }

      const phoneError = validatePhone(phone);
      if (phoneError) {
        setErrors({ phone: phoneError });
        return;
      }

      if (!fullName.trim()) {
        setErrors({ fullName: 'Full name is required' });
        return;
      }
    }

    setLoading(true);
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email, password }
        : { email, password, full_name: fullName, phone, organization };
      
      const { data } = await api.post(endpoint, payload);
      localStorage.setItem('token', data.access_token);

      // Check if user has active subscription
      try {
        const ordersRes = await api.get('/orders');
        const hasActive = ordersRes.data.some((order: any) => order.status === 'paid');
        router.push(hasActive ? '/dashboard' : '/subscribe');
      } catch {
        router.push('/subscribe');
      }
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

      <div className="flex gap-2 p-1 glass rounded-full mb-8">
        <button
          onClick={() => setIsLogin(true)}
          className={`flex-1 py-2 rounded-full transition-all ${
            isLogin ? 'bg-white/20' : 'hover:bg-white/5'
          }`}
        >
          Login
        </button>
        <button
          onClick={() => setIsLogin(false)}
          className={`flex-1 py-2 rounded-full transition-all ${
            !isLogin ? 'bg-white/20' : 'hover:bg-white/5'
          }`}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs opacity-70 mb-1">Email</label>
          <input
            type="email"
            className={`input ${errors.email ? 'border-red-500/50' : ''}`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {errors.email && <p className="text-xs text-red-400 mt-1">{errors.email}</p>}
        </div>
        <div>
          <label className="block text-xs opacity-70 mb-1">Password</label>
          <input
            type="password"
            className={`input ${errors.password ? 'border-red-500/50' : ''}`}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {errors.password && <p className="text-xs text-red-400 mt-1">{errors.password}</p>}
        </div>
        {!isLogin && (
          <>
            <div>
              <label className="block text-xs opacity-70 mb-1">Full Name</label>
              <input
                type="text"
                className={`input ${errors.fullName ? 'border-red-500/50' : ''}`}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
              {errors.fullName && <p className="text-xs text-red-400 mt-1">{errors.fullName}</p>}
            </div>
            <div>
              <label className="block text-xs opacity-70 mb-1">Phone</label>
              <input
                type="tel"
                className={`input ${errors.phone ? 'border-red-500/50' : ''}`}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="081234567890"
                required
              />
              {errors.phone && <p className="text-xs text-red-400 mt-1">{errors.phone}</p>}
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
        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary w-full mt-6"
        >
          {loading ? 'Processing...' : isLogin ? 'Login' : 'Register'}
        </button>
      </form>
    </div>
  );
}
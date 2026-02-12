'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import PackageCard from '@/components/PackageCard';

interface Package {
  id: number;
  name: string;
  price: number;
  duration_days: number;
  max_clients: number;
}

interface Order {
  id: number;
  order_code: string;
  amount: number;
}

export default function SubscribePage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(false);
  const [currentOrder, setCurrentOrder] = useState<Order | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/');
      return;
    }
    fetchPackages();
  }, []);

  const fetchPackages = async () => {
    try {
      const { data } = await api.get('/packages');
      setPackages(data);
    } catch (error) {
      console.error('Failed to fetch packages', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPackage = async (pkg: Package) => {
    setSubscribing(true);
    try {
      const { data } = await api.post('/orders', { package_id: pkg.id });
      setCurrentOrder({
        id: data.order_id,
        order_code: data.order_code,
        amount: data.amount,
      });
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create order');
    } finally {
      setSubscribing(false);
    }
  };

  const handleMockPayment = async () => {
    if (!currentOrder) return;
    try {
      await api.post(`/orders/${currentOrder.id}/mock-pay`);
      router.push('/dashboard');
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Payment failed');
    }
  };

  const cancelOrder = () => {
    setCurrentOrder(null);
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="glass p-6">Loading packages...</div>
      </div>
    );
  }

  if (currentOrder) {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-light flex items-center justify-center gap-2">
            <i className="fas fa-qrcode"></i> Scan to Pay
          </h1>
          <p className="text-sm opacity-70 mt-2">
            Order #{currentOrder.order_code}
          </p>
        </div>

        <div className="glass p-8 flex flex-col items-center">
          <div className="w-48 h-48 bg-white/10 border-2 border-white/30 rounded-xl flex items-center justify-center mb-4">
            <i className="fas fa-qrcode text-8xl opacity-50"></i>
          </div>
          <div className="text-center mb-4">
            <p className="text-lg font-medium">Rp {currentOrder.amount.toLocaleString()}</p>
            <p className="text-xs opacity-70 mt-1">QRIS – Mock Payment</p>
          </div>

          <button
            onClick={handleMockPayment}
            className="btn btn-success w-full mb-2"
          >
            <i className="fas fa-check-circle mr-2"></i> Simulate Payment
          </button>
          <button
            onClick={cancelOrder}
            className="btn w-full"
          >
            Cancel
          </button>

          <p className="text-xs opacity-50 mt-4 text-center">
            This is a development mock. Real QRIS will appear here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="text-center mb-8">
        <h1 className="text-3xl font-light flex items-center justify-center gap-2">
          <i className="fas fa-box"></i> Choose Your Plan
        </h1>
        <p className="text-sm opacity-70 mt-2">
          Select a package to activate your subscription
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {packages.map((pkg) => (
          <PackageCard
            key={pkg.id}
            pkg={pkg}
            onSelect={handleSelectPackage}
            disabled={subscribing}
          />
        ))}
      </div>

      {subscribing && (
        <div className="mt-8 glass p-4 text-center">
          Creating your order...
        </div>
      )}

      <div className="mt-8 text-center">
        <button
          onClick={() => {
            localStorage.removeItem('token');
            router.push('/');
          }}
          className="btn btn-sm"
        >
          <i className="fas fa-sign-out-alt mr-1"></i> Logout
        </button>
      </div>
    </div>
  );
}
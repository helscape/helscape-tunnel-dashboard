mkdir -p app/dashboard
cat > app/dashboard/page.tsx << 'EOF'
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import PackageCard from '@/components/PackageCard';
import ClientCard from '@/components/ClientCard';

interface User {
  id: number;
  email: string;
  full_name: string;
  organization: string;
}

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
  status: string;
  package_id: number;
  expires_at: string;
  created_at: string;
  paid_at?: string;
}

interface Client {
  id: number;
  name: string;
  client_ip: string;
  server_endpoint: string;
  server_port: number;
  status: string;
}

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [packages, setPackages] = useState<Package[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/');
      return;
    }
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [meRes, packagesRes, ordersRes, clientsRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/packages'),
        api.get('/orders'),
        api.get('/clients'),
      ]);
      setUser(meRes.data);
      setPackages(packagesRes.data);
      setOrders(ordersRes.data);
      setClients(clientsRes.data);
    } catch (error: any) {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPackage = async (pkg: Package) => {
    try {
      const { data } = await api.post('/orders', { package_id: pkg.id });
      await api.post(`/orders/${data.order_id}/mock-pay`);
      alert(`Package ${pkg.name} activated!`);
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Order failed');
    }
  };

  const handleClientDeleted = (clientId: number) => {
    setClients(clients.filter((c) => c.id !== clientId));
  };

  const createClient = async () => {
    const name = prompt('Device name:');
    if (!name) return;
    try {
      await api.post('/clients', { name, enable_nat: true, duration_days: 30 });
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Creation failed');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="glass p-6">Loading dashboard...</div>
      </div>
    );
  }

  const activeSubscription = orders.find((o) => o.status === 'paid');
  const packageMap = new Map(packages.map((p) => [p.id, p]));
  const currentPackage = activeSubscription ? packageMap.get(activeSubscription.package_id) : null;

  return (
    <>
      <div className="flex flex-wrap justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-light flex items-center gap-2">
            <i className="fas fa-shield-halbed"></i> Dashboard
          </h1>
          <p className="text-sm opacity-70 mt-1">
            {user?.full_name} · {user?.organization}
          </p>
        </div>
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

      {activeSubscription ? (
        <div className="glass p-5 mb-8 flex flex-wrap items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="badge bg-green-500/20 border-green-400/50">ACTIVE</span>
            <span>Expires: {new Date(activeSubscription.expires_at).toLocaleDateString()}</span>
          </div>
          <div className="text-sm opacity-80">
            Clients: {clients.length} / {currentPackage?.max_clients || '?'}
          </div>
        </div>
      ) : (
        <div className="glass p-5 mb-8 border-yellow-500/30 bg-yellow-500/5">
          <span className="badge bg-yellow-500/20 border-yellow-400/50">NO ACTIVE SUBSCRIPTION</span>
          <p className="text-sm mt-2">Choose a package below to start.</p>
        </div>
      )}

      <section className="mb-12">
        <h2 className="text-xl font-medium mb-4 flex items-center gap-2">
          <i className="fas fa-box"></i> Available Plans
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {packages.map((pkg) => (
            <PackageCard key={pkg.id} pkg={pkg} onSelect={handleSelectPackage} />
          ))}
        </div>
      </section>

      <section className="mb-12">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-medium flex items-center gap-2">
            <i className="fas fa-network-wired"></i> Your Devices
          </h2>
          <button
            onClick={createClient}
            className="btn btn-sm btn-primary"
            disabled={!activeSubscription}
          >
            <i className="fas fa-plus mr-1"></i> New Client
          </button>
        </div>
        {clients.length === 0 ? (
          <div className="glass p-10 text-center opacity-70">
            <i className="fas fa-wifi text-3xl mb-3 opacity-50"></i>
            <p>No WireGuard clients yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {clients.map((client) => (
              <ClientCard key={client.id} client={client} onDeleted={handleClientDeleted} />
            ))}
          </div>
        )}
      </section>

      {orders.length > 0 && (
        <section>
          <h2 className="text-xl font-medium mb-4 flex items-center gap-2">
            <i className="fas fa-history"></i> Order History
          </h2>
          <div className="space-y-3">
            {orders.map((order) => (
              <div key={order.id} className="glass p-4 flex flex-wrap justify-between items-center">
                <div>
                  <span className="font-mono text-sm">{order.order_code}</span>
                  <span
                    className={`badge ml-3 ${
                      order.status === 'paid' ? 'bg-green-500/20' : 'bg-gray-500/20'
                    }`}
                  >
                    {order.status}
                  </span>
                </div>
                <div className="text-sm opacity-80">
                  Rp {order.amount.toLocaleString()} · {new Date(order.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
EOF

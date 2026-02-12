'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import TrafficChart from '@/components/TrafficChart';
import CreateDeviceModal from '@/components/CreateDeviceModal'; 

interface User {
  id: number;
  email: string;
  full_name: string;
  organization: string;
}

interface Client {
  id: number;
  name: string;
  client_ip: string;
  gateway_ip: string;
  server_endpoint: string;
  server_port: number;
  status: string;
  last_handshake: string | null;
  rx_bytes: number;
  tx_bytes: number;
  nat_mappings?: Record<string, number>;
  expires_at?: string;
}

interface Order {
  id: number;
  package_id: number;
  status: string;
  expires_at: string;
  created_at: string;
}

interface Package {
  id: number;
  name: string;
  price: number;
  duration_days: number;
  max_clients: number;
}

const serviceNames: Record<string, string> = {
  dapodik: 'Dapodik',
  erapor_sd: 'E-Rapor SD',
  erapor_smp: 'E-Rapor SMP',
  https: 'HTTPS',
};

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);
  const [packageInfo, setPackageInfo] = useState<Package | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
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
      const [meRes, clientsRes, ordersRes, packagesRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/clients'),
        api.get('/orders'),
        api.get('/packages'),
      ]);

      setUser(meRes.data);
      setClient(clientsRes.data[0] || null);

      const active = ordersRes.data.find((o: Order) => o.status === 'paid');
      setActiveOrder(active || null);

      if (active) {
        const pkg = packagesRes.data.find((p: Package) => p.id === active.package_id);
        setPackageInfo(pkg || null);
      }
    } catch (error: any) {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        router.push('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDevice = async (deviceName: string) => {
    setCreating(true);
    setShowCreateModal(false);
    try {
      await api.post('/clients', {
        name: deviceName,
        enable_nat: true,
        duration_days: 30,
      });
      await fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create device');
    } finally {
      setCreating(false);
    }
  };

  const downloadConfig = async () => {
    if (!client) return;
    setDownloading(true);
    try {
      const response = await api.get(`/clients/${client.id}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${client.name}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Failed to download configuration');
    } finally {
      setDownloading(false);
    }
  };

  const deleteClient = async () => {
    if (!client) return;
    if (!confirm(`Delete device "${client.name}"?`)) return;
    try {
      await api.delete(`/clients/${client.id}`);
      setClient(null);
    } catch {
      alert('Failed to delete device');
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  const getServiceList = () => {
    if (!client?.nat_mappings) return [];
    return Object.entries(client.nat_mappings)
      .filter(([_, port]) => port != null)
      .map(([key, port]) => ({
        name: serviceNames[key] || key,
        host: client.server_endpoint,
        port,
        full: `${client.server_endpoint}:${port}`,
      }));
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="glass p-6">Loading dashboard...</div>
      </div>
    );
  }

  const services = client ? getServiceList() : [];

  return (
    <>
      {/* ========== HEADER ========== */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <h1 className="text-3xl font-light flex items-center gap-2">
          <i className="fas fa-shield-halbed"></i> Dashboard
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-sm opacity-80">
            Hello, {user?.full_name || 'User'}
          </span>
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

      {/* ========== NO DEVICE STATE ========== */}
      {!client ? (
        <div className="max-w-md mx-auto mt-12">
          <div className="glass-card text-center p-8">
            <i className="fas fa-wifi text-4xl mb-4 opacity-70"></i>
            <h2 className="text-xl font-medium mb-2">No VPN Device</h2>
            <p className="text-sm opacity-80 mb-6">
              You haven't created a VPN device yet. Create one now to access your services.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              disabled={creating}
              className="btn btn-primary px-8 py-3"
            >
              {creating ? 'Creating...' : 'Create Device'}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* ========== TOP ROW: SERVICE ACCESS + CONFIG DOWNLOAD ========== */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
            {/* Service Access Area */}
            <div className="lg:col-span-3">
              <div className="glass p-6">
                <div className="text-xs uppercase tracking-wider opacity-60 mb-4">
                  <i className="fas fa-door-open mr-1"></i> Service Access
                </div>
                {services.length === 0 ? (
                  <p className="text-sm opacity-70">No NAT services configured.</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {services.map((svc) => (
                      <div key={svc.port} className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <div className="text-xs font-semibold uppercase tracking-wider text-blue-300 mb-1">
                          {svc.name}
                        </div>
                        <div className="font-mono text-sm md:text-base break-all">
                          {svc.full}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-xs opacity-60 mt-4">
                  Use these addresses to access your services from your device.
                </div>
              </div>
            </div>

            {/* Download Card */}
            <div className="lg:col-span-1">
              <div className="glass p-5 h-full flex flex-col items-center justify-center text-center">
                <i className="fas fa-file-archive text-3xl mb-3 opacity-80"></i>
                <h3 className="font-medium mb-2">VPN Configuration</h3>
                <p className="text-xs opacity-70 mb-3">
                  {client.name}
                </p>
                <button
                  onClick={downloadConfig}
                  disabled={downloading}
                  className="btn btn-sm btn-primary w-full"
                >
                  <i className="fas fa-download mr-1"></i>
                  {downloading ? 'Downloading...' : 'Download .conf'}
                </button>
                <button
                  onClick={deleteClient}
                  className="btn btn-sm btn-danger w-full mt-2"
                >
                  <i className="fas fa-trash mr-1"></i>
                  Delete
                </button>
              </div>
            </div>
          </div>

          {/* ========== MAIN GRID ========== */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* LEFT: Device Status & VPN IP */}
            <div className="lg:col-span-1 space-y-4">
              <div className="glass p-5">
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <i className="fas fa-signal"></i> Device Status
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs opacity-70">Connection</span>
                    <span
                      className={`badge ${
                        client.status === 'online'
                          ? 'bg-green-500/20 border-green-400/50'
                          : 'bg-gray-500/20'
                      }`}
                    >
                      {client.status === 'online' ? '🟢 Online' : '⚫ Offline'}
                    </span>
                  </div>
                  {client.last_handshake && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs opacity-70">Last handshake</span>
                      <span className="text-xs">
                        {new Date(client.last_handshake).toLocaleString()}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-xs opacity-70">VPN IP</span>
                    <span className="text-xs font-mono">{client.client_ip}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs opacity-70">Expires</span>
                    <span className="text-xs">
                      {client.expires_at
                        ? new Date(client.expires_at).toLocaleDateString()
                        : 'Never'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* RIGHT: Subscription & Traffic */}
            <div className="lg:col-span-2 space-y-4">
              {activeOrder && packageInfo && (
                <div className="glass p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                    <h3 className="text-sm font-medium flex items-center gap-2">
                      <i className="fas fa-crown"></i> Active Plan
                    </h3>
                    <span className="badge bg-blue-500/20 border-blue-400/50">
                      {packageInfo.name}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="opacity-70 block">Subscribed</span>
                      <span className="font-medium">
                        {new Date(activeOrder.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div>
                      <span className="opacity-70 block">Expires</span>
                      <span className="font-medium">
                        {activeOrder.expires_at
                          ? new Date(activeOrder.expires_at).toLocaleDateString()
                          : '∞'}
                      </span>
                    </div>
                    <div>
                      <span className="opacity-70 block">Price</span>
                      <span className="font-medium">
                        Rp {packageInfo.price.toLocaleString('id-ID')}
                      </span>
                    </div>
                    <div>
                      <span className="opacity-70 block">Max Devices</span>
                      <span className="font-medium">{packageInfo.max_clients}</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="glass p-5">
                <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
                  <h3 className="text-sm font-medium flex items-center gap-2">
                    <i className="fas fa-chart-simple"></i> Today's Traffic
                  </h3>
                  <span className="text-xs opacity-70">
                    ↓ {formatBytes(client.rx_bytes)}  /  ↑ {formatBytes(client.tx_bytes)}
                  </span>
                </div>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Download</span>
                      <span>{formatBytes(client.rx_bytes)}</span>
                    </div>
                    <div className="w-full bg-black/30 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${Math.min((client.rx_bytes / (1024 * 1024 * 100)) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Upload</span>
                      <span>{formatBytes(client.tx_bytes)}</span>
                    </div>
                    <div className="w-full bg-black/30 rounded-full h-2">
                      <div
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{ width: `${Math.min((client.tx_bytes / (1024 * 1024 * 100)) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              <TrafficChart rxBytes={client.rx_bytes} txBytes={client.tx_bytes} />
            </div>
          </div>
        </>
      )}

      {/* ========== CREATE DEVICE MODAL ========== */}
      <CreateDeviceModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateDevice}
        isCreating={creating}
      />
    </>
  );
}
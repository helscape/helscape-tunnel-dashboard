cat > components/ClientCard.tsx << 'EOF'
import { useState } from 'react';
import api from '@/lib/api';

interface Client {
  id: number;
  name: string;
  client_ip: string;
  server_endpoint: string;
  server_port: number;
  status: string;
}

export default function ClientCard({ client, onDeleted }: { client: Client; onDeleted: (id: number) => void }) {
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const downloadConfig = async () => {
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
      alert('Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const deleteClient = async () => {
    if (!confirm(`Delete client "${client.name}"?`)) return;
    setDeleting(true);
    try {
      await api.delete(`/clients/${client.id}`);
      onDeleted(client.id);
    } catch {
      alert('Delete failed');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="glass-card">
      <div className="flex justify-between items-start mb-3">
        <h4 className="font-medium text-lg">{client.name}</h4>
        <span
          className={`badge ${
            client.status === 'online' ? 'bg-green-500/20 border-green-400/50' : 'bg-gray-500/20'
          }`}
        >
          {client.status}
        </span>
      </div>
      <p className="text-xs opacity-70 mb-1">VPN IP: {client.client_ip}</p>
      <p className="text-xs opacity-70 mb-4">
        Endpoint: {client.server_endpoint}:{client.server_port}
      </p>
      <div className="flex gap-2">
        <button
          onClick={downloadConfig}
          disabled={downloading}
          className="btn btn-sm flex-1"
        >
          <i className="fas fa-download mr-1"></i> {downloading ? '...' : 'Config'}
        </button>
        <button
          onClick={deleteClient}
          disabled={deleting}
          className="btn btn-sm btn-danger flex-1"
        >
          <i className="fas fa-trash mr-1"></i> {deleting ? '...' : 'Delete'}
        </button>
      </div>
    </div>
  );
}
EOF

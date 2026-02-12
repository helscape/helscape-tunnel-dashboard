'use client';

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface TrafficChartProps {
  rxBytes: number;
  txBytes: number;
}

export default function TrafficChart({ rxBytes, txBytes }: TrafficChartProps) {
  // Mock historical data – replace with real backend later
  const data = [
    { name: 'Mon', rx: 1.2, tx: 0.8 },
    { name: 'Tue', rx: 2.4, tx: 1.5 },
    { name: 'Wed', rx: 3.1, tx: 2.2 },
    { name: 'Thu', rx: 4.0, tx: 3.0 },
    { name: 'Fri', rx: 5.2, tx: 3.8 },
    { name: 'Sat', rx: 6.1, tx: 4.5 },
    { name: 'Sun', rx: 7.3, tx: 5.2 },
  ];

  // Format bytes to human readable (MB/GB)
  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  // Current totals
  const currentRx = rxBytes;
  const currentTx = txBytes;

  return (
    <div className="glass p-4">
      <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
        <i className="fas fa-chart-line"></i> Traffic (last 7 days)
      </h3>

      {/* Current session totals */}
      <div className="flex justify-between text-xs mb-4">
        <span className="opacity-70">⬇️ Download: {formatBytes(currentRx)}</span>
        <span className="opacity-70">⬆️ Upload: {formatBytes(currentTx)}</span>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="rxColor" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="txColor" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
          <YAxis stroke="#9ca3af" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(20,25,35,0.9)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: 'white',
            }}
          />
          <Area
            type="monotone"
            dataKey="rx"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#rxColor)"
            name="Download"
          />
          <Area
            type="monotone"
            dataKey="tx"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#txColor)"
            name="Upload"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
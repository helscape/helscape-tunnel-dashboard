cat > components/PackageCard.tsx << 'EOF'
interface Package {
  id: number;
  name: string;
  price: number;
  duration_days: number;
  max_clients: number;
}

export default function PackageCard({ pkg, onSelect }: { pkg: Package; onSelect: (pkg: Package) => void }) {
  return (
    <div className="glass-card flex flex-col h-full">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-medium">{pkg.name}</h3>
        <span className="badge">{pkg.max_clients} devices</span>
      </div>
      <div className="text-3xl font-light mb-2">
        Rp {pkg.price.toLocaleString()}
        <span className="text-sm font-normal opacity-70">/mo</span>
      </div>
      <p className="text-sm opacity-80 mb-6">{pkg.duration_days} days validity</p>
      <button
        onClick={() => onSelect(pkg)}
        className="btn btn-primary w-full mt-auto"
      >
        Select Plan
      </button>
    </div>
  );
}
EOF

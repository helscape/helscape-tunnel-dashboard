#!/bin/bash

# ============================================
# CLEANUP TESTING CLUTTER – VPN SaaS
# Hapus semua data testing dari DB + MikroTik
# ============================================

set -e  # exit jika ada error

# ---------- KONFIGURASI ----------
# Isi sesuai environment Anda
DB_CONTAINER="mariadb"          # nama container MariaDB
DB_NAME="vpn_saas"
DB_USER="root"
DB_PASS="superpower"          # ganti dengan password asli

MIKROTIK_HOST="172.31.5.31"
MIKROTIK_USER="admin"
MIKROTIK_PASS="fabian27"
MIKROTIK_USE_SSL=false          # true jika pakai HTTPS
# ---------------------------------

echo "🧹 MEMULAI CLEANUP..."
echo "=============================="

# ---------- 1. BERSIHKAN DATABASE ----------
echo "🗄️  Membersihkan database..."
docker exec -i "$DB_CONTAINER" mariadb -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" <<EOF
-- Hapus semua client VPN
DELETE FROM wg_clients;

-- Hapus semua orders
DELETE FROM orders;

-- Hapus semua users (HATI-HATI! komentar jika ingin keep)
DELETE FROM users;

-- Reset auto increment (opsional)
ALTER TABLE wg_clients AUTO_INCREMENT = 1;
ALTER TABLE orders AUTO_INCREMENT = 1;
ALTER TABLE users AUTO_INCREMENT = 1;
EOF

echo "✅ Database cleaned."

# ---------- 2. BERSIHKAN MIKROTIK ----------
echo "🛜  Membersihkan MikroTik..."

# Tentukan base URL REST API
if [ "$MIKROTIK_USE_SSL" = true ]; then
    PROTO="https"
    PORT=""
else
    PROTO="http"
    PORT=""
fi
BASE_URL="$PROTO://$MIKROTIK_HOST/rest"

# Helper function untuk curl dengan basic auth
mtik() {
    curl -s -u "$MIKROTIK_USER:$MIKROTIK_PASS" \
         -H "Content-Type: application/json" \
         "${BASE_URL}$1" "${@:2}"
}

# Hapus semua WireGuard interface dengan nama mengandung "wg_"
echo "   → Menghapus WireGuard interfaces..."
INTERFACES=$(mtik "/interface/wireguard" | jq -r '.[] | select(.name | startswith("wg_")) | .".id"')
for id in $INTERFACES; do
    mtik "/interface/wireguard/$id" -X DELETE
    echo "     - Interface $id dihapus"
done

# Hapus semua NAT rules dengan comment mengandung "wg_"
echo "   → Menghapus NAT rules..."
RULES=$(mtik "/ip/firewall/nat" | jq -r '.[] | select(.comment | contains("wg_")) | .".id"')
for id in $RULES; do
    mtik "/ip/firewall/nat/$id" -X DELETE
    echo "     - NAT rule $id dihapus"
done

# Hapus semua scheduler dengan nama mengandung "EXP_"
echo "   → Menghapus schedulers..."
SCHEDS=$(mtik "/system/scheduler" | jq -r '.[] | select(.name | startswith("EXP_")) | .".id"')
for id in $SCHEDS; do
    mtik "/system/scheduler/$id" -X DELETE
    echo "     - Scheduler $id dihapus"
done

echo "✅ MikroTik cleaned."
echo "=============================="
echo "🎉 Cleanup selesai! DB & MikroTik sudah bersih."

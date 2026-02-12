from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import io
import zipfile
import uuid
import re

from app.config import settings
from app.database import init_db, get_db, User, WGClient, Order, Package
from app.mikrotik import MikrotikAPI, MikrotikResourceManager, WireGuardManager
from app.auth import create_access_token, verify_token, get_password_hash, verify_password

app = FastAPI(title="VPN Pro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ---------- Validation Helpers ----------
def validate_email(email: str):
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise HTTPException(status_code=400, detail="Invalid email format")

def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")

def validate_phone(phone: str):
    if not re.match(r"^[0-9]{10,13}$", phone):
        raise HTTPException(status_code=400, detail="Phone must be 10-13 digits (numbers only)")

# ---------- Startup ----------
@app.on_event("startup")
async def startup():
    await init_db()

# ---------- Auth ----------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = verify_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    return user

@app.post("/auth/login")
async def login(credentials: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == credentials["email"]))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials["password"], user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/register")
async def register(data: dict, db: AsyncSession = Depends(get_db)):
    # ---------- Validation ----------
    validate_email(data["email"])
    validate_password(data["password"])
    validate_phone(data["phone"])
    
    # ---------- Check existing ----------
    result = await db.execute(select(User).where(User.email == data["email"]))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # ---------- Create user ----------
    user = User(
        email=data["email"],
        hashed_password=get_password_hash(data["password"]),
        full_name=data["full_name"],
        phone=data["phone"],
        organization=data["organization"],
    )
    db.add(user)
    await db.flush()
    
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id}

@app.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization": user.organization,
    }

# ---------- WireGuard Clients (Single Device) ----------
@app.get("/clients")
async def list_clients(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WGClient).where(WGClient.user_id == user.id, WGClient.is_active == True)
    )
    clients = result.scalars().all()
    
    if not clients:
        return []
    
    # MikroTik status fetch (only if client exists)
    mt = MikrotikAPI(
        settings.MIKROTIK_HOST,
        settings.MIKROTIK_USER,
        settings.MIKROTIK_PASS,
        use_ssl=settings.MIKROTIK_USE_SSL,
        verify_ssl=settings.MIKROTIK_VERIFY_SSL,
    )
    
    client = clients[0]  # only one client
    stats = await WireGuardManager(mt, None).get_client_stats(client.interface_name)
    
    return [{
        "id": client.id,
        "name": client.client_name,
        "client_ip": client.client_ip,
        "gateway_ip": client.gateway_ip,
        "server_endpoint": client.server_endpoint,
        "server_port": client.server_port,
        "status": "online" if (stats and stats.get("enabled")) else "offline",
        "last_handshake": stats.get("last_handshake") if stats else None,
        "rx_bytes": stats.get("rx_bytes", 0) if stats else 0,
        "tx_bytes": stats.get("tx_bytes", 0) if stats else 0,
        "nat_mappings": client.nat_mappings,
        "expires_at": client.expires_at.isoformat() if client.expires_at else None,
    }]

@app.post("/clients")
async def create_client(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ---------- Active subscription check ----------
    result = await db.execute(
        select(Order)
        .where(
            Order.user_id == user.id,
            Order.status == "paid",
            Order.expires_at > datetime.utcnow()
        )
        .order_by(Order.created_at.desc())
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=403, detail="No active subscription")
    
    # ---------- SINGLE DEVICE LOCK ----------
    existing = await db.execute(
        select(WGClient).where(
            WGClient.user_id == user.id,
            WGClient.is_active == True
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail="Only one device allowed. Delete existing device first."
        )
    
    # ---------- Package limit check ----------
    result = await db.execute(select(Package).where(Package.id == order.package_id))
    package = result.scalar_one()
    # (already enforced by single device, but keep for safety)
    
    # ---------- MikroTik provisioning ----------
    mt = MikrotikAPI(
        settings.MIKROTIK_HOST,
        settings.MIKROTIK_USER,
        settings.MIKROTIK_PASS,
        use_ssl=settings.MIKROTIK_USE_SSL,
        verify_ssl=settings.MIKROTIK_VERIFY_SSL,
    )
    res_mgr = MikrotikResourceManager(mt)
    wg_mgr = WireGuardManager(mt, res_mgr)
    
    try:
        provisioned = await wg_mgr.provision(
            data["name"],
            "10.200.0.0/16",
            data.get("enable_nat", True),
            data.get("duration_days", 30)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    expires = None
    if data.get("duration_days", 0) > 0:
        expires = datetime.utcnow() + timedelta(days=data["duration_days"])
    
    client = WGClient(
        user_id=user.id,
        order_id=order.id,
        client_name=data["name"],
        client_ip=provisioned["client_ip"],
        gateway_ip=provisioned["gateway_ip"],
        server_public_key=provisioned["server_public_key"],
        server_endpoint=provisioned["server_endpoint"],
        server_port=provisioned["server_port"],
        client_private_key=provisioned["client_private_key"],
        interface_name=provisioned["interface_name"],
        mikrotik_peer_id=provisioned["mikrotik_peer_id"],
        nat_enabled=data.get("enable_nat", False),
        nat_mappings=provisioned["nat_mappings"],
        expires_at=expires,
    )
    db.add(client)
    await db.flush()
    
    return {
        "id": client.id,
        "name": data["name"],
        "client_ip": provisioned["client_ip"],
        "server_public_key": provisioned["server_public_key"],
    }

@app.get("/clients/{client_id}/download")
async def download_config(
    client_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WGClient).where(WGClient.id == client_id, WGClient.user_id == user.id, WGClient.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    conf = f"""[Interface]
PrivateKey = {client.client_private_key}
Address = {client.client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {client.server_public_key}
Endpoint = {client.server_endpoint}:{client.server_port}
AllowedIPs = 10.200.0.0/16
PersistentKeepalive = 25
"""
    
    info = f"""CLIENT: {client.client_name}
VPN IP: {client.client_ip}
GATEWAY: {client.gateway_ip}
SERVER: {client.server_endpoint}:{client.server_port}
EXPIRES: {client.expires_at or 'Never'}

NAT MAPPINGS:
"""
    if client.nat_mappings:
        for svc, port in client.nat_mappings.items():
            info += f"  {svc}: {client.server_endpoint}:{port}\n"
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{client.client_name}.conf", conf)
        zf.writestr(f"{client.client_name}_info.txt", info)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={client.client_name}_config.zip"}
    )

@app.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WGClient).where(WGClient.id == client_id, WGClient.user_id == user.id, WGClient.is_active == True)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    mt = MikrotikAPI(
        settings.MIKROTIK_HOST,
        settings.MIKROTIK_USER,
        settings.MIKROTIK_PASS,
        use_ssl=settings.MIKROTIK_USE_SSL,
        verify_ssl=settings.MIKROTIK_VERIFY_SSL,
    )
    
    await WireGuardManager(mt, None).delete_client(client.interface_name)
    
    client.is_active = False
    await db.flush()
    
    return {"success": True}

# ---------- Packages ----------
@app.get("/packages")
async def list_packages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package))
    packages = result.scalars().all()
    return [{"id": p.id, "name": p.name, "price": float(p.price), "duration_days": p.duration_days, "max_clients": p.max_clients} for p in packages]

@app.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    packages = [
        Package(name="Basic", price=150000, duration_days=30, max_clients=1, features={"nat": True}),
        Package(name="Professional", price=350000, duration_days=30, max_clients=3, features={"nat": True}),
        Package(name="Enterprise", price=800000, duration_days=30, max_clients=10, features={"nat": True}),
    ]
    for p in packages:
        db.add(p)
    await db.flush()
    return {"seeded": True}

# ---------- Orders & Payment ----------
@app.post("/orders")
async def create_order(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    package_id = data.get("package_id")
    if not package_id:
        raise HTTPException(status_code=400, detail="package_id required")
    
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    order_code = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    order = Order(
        user_id=user.id,
        package_id=package.id,
        order_code=order_code,
        amount=package.price,
        status="pending",
        payment_method="qris",
        payment_payload={},
        paid_at=None,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        created_at=datetime.utcnow()
    )
    db.add(order)
    await db.flush()
    
    return {
        "order_id": order.id,
        "order_code": order.order_code,
        "amount": float(order.amount),
        "status": order.status,
        "expires_at": order.expires_at.isoformat(),
        "payment": {
            "method": "qris",
            "qr_url": None,
            "instructions": "Click 'Simulate Payment' to complete order."
        }
    }

@app.post("/orders/{order_id}/mock-pay")
async def mock_pay_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == "paid":
        return {"message": "Order already paid"}
    
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order is {order.status}, cannot pay")
    
    result = await db.execute(select(Package).where(Package.id == order.package_id))
    package = result.scalar_one()
    
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    order.expires_at = datetime.utcnow() + timedelta(days=package.duration_days)
    
    await db.flush()
    
    return {
        "order_id": order.id,
        "status": "paid",
        "paid_at": order.paid_at.isoformat(),
        "expires_at": order.expires_at.isoformat()
    }

@app.get("/orders")
async def list_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [
        {
            "id": o.id,
            "order_code": o.order_code,
            "amount": float(o.amount),
            "status": o.status,
            "package_id": o.package_id,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "created_at": o.created_at.isoformat()
        }
        for o in orders
    ]
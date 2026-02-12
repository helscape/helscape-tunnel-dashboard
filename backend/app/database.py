from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, DECIMAL, ForeignKey, JSON, select;
from datetime import datetime

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    phone = Column(String(20))
    organization = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Package(Base):
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    price = Column(DECIMAL(10, 2))
    duration_days = Column(Integer)
    max_clients = Column(Integer, default=1)
    features = Column(JSON)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    package_id = Column(Integer, ForeignKey("packages.id"))
    order_code = Column(String(50), unique=True)
    amount = Column(DECIMAL(10, 2))
    status = Column(String(20), default="pending")
    payment_method = Column(String(20))
    payment_payload = Column(JSON)
    paid_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class WGClient(Base):
    __tablename__ = "wg_clients"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    client_name = Column(String(32), unique=True)
    client_ip = Column(String(15))
    gateway_ip = Column(String(15))
    server_public_key = Column(Text)
    server_endpoint = Column(String(255))
    server_port = Column(Integer)
    client_private_key = Column(Text)
    interface_name = Column(String(50))
    nat_enabled = Column(Boolean, default=False)
    nat_mappings = Column(JSON)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    mikrotik_peer_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_handshake = Column(DateTime)
    rx_bytes = Column(Integer, default=0)
    tx_bytes = Column(Integer, default=0)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
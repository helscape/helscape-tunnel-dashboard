from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional  

class Settings(BaseSettings):
    DEBUG: bool = False
    SECRET_KEY: str = "change-this"
    JWT_SECRET: str = "jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = "mysql+aiomysql://vpn_user:password@localhost/vpn_saas"
    
    MIKROTIK_HOST: str = "192.168.88.1"
    MIKROTIK_USER: str = "admin"
    MIKROTIK_PASS: str = ""
    MIKROTIK_USE_SSL: bool = True
    MIKROTIK_VERIFY_SSL: bool = False
    
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""
    MIDTRANS_SANDBOX: bool = True
    
    class ConfigDict:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

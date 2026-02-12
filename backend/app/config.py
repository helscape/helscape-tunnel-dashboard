from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: Optional[str] = None

    # JWT
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email (opsional)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Database echo flag
    DB_ECHO: bool = False

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Xendit Configuration
    XENDIT_SECRET_KEY: str = ""
    XENDIT_WEBHOOK_TOKEN: str = ""
    XENDIT_API_BASE_URL: str = "https://api.xendit.co"

    class Config:
        env_file = ".env"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret_key_length(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

settings = Settings()
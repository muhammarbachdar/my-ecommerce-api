from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
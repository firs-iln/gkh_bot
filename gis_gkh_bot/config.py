from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    TOKEN: SecretStr
    REDIS_HOST: str
    DADATA_TOKEN: SecretStr
    DADATA_SECRET: SecretStr
    DB_URI: SecretStr
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


config = Settings()

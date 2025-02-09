from pydantic.v1 import BaseSettings



class Settings(BaseSettings):
    SERVICE_ACCOUNT_LOGIN: str
    SERVICE_ACCOUNT_PASSWORD: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()

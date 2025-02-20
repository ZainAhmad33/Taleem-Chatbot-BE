from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api: str
    
    model_config = SettingsConfigDict(env_file=".env")
    

settings = Settings()
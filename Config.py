from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api: str
    contextualize_llm: str
    chat_llm: str
    embeddings_model: str
    physics_9th_collection: str
    biology_9th_collection: str
    
    model_config = SettingsConfigDict(env_file=".env")
    

settings = Settings()
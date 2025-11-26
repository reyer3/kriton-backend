from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
load_dotenv()
class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    
    # Ollama
    OLLAMA_HOST: str
    OLLAMA_MODEL: str

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"
    
    # Provider
    LLM_PROVIDER: str = "ollama"
    
    # API
    API_HOST: str
    API_PORT: int
    API_RELOAD: bool
    
    # Redis (opcional para cache)
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    USE_REDIS: bool
    
    # Limites
    MAX_QUERY_RESULTS: int = 1000
    CONVERSATION_HISTORY_LIMIT: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///data/autoapply.db"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    LLM_TIMEOUT: int = 120
    SEARCH_QUERIES: str = "Strategy Operations Analyst,Business Transformation Consultant,Management Consulting entry level"
    TARGET_LOCATIONS: str = "United States,Remote"
    MAX_JOBS_PER_CYCLE: int = 10
    CYCLES_PER_RUN: int = 10
    HEADLESS_BROWSER: bool = True
    SCREENSHOT_ON_APPLY: bool = True
    APPLY_DELAY_SECONDS: int = 5
    RUN_TIMES: str = "08:00,18:00"
    
    @property
    def search_query_list(self): return [q.strip() for q in self.SEARCH_QUERIES.split(",")]
    @property
    def location_list(self): return [l.strip() for l in self.TARGET_LOCATIONS.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()

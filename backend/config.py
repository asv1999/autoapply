from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///data/autoapply.db"
    
    # LLM — Groq (primary, free) + Ollama (fallback, offline)
    GROQ_API_KEY: str = ""  # Get free key at console.groq.com
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    LLM_TIMEOUT: int = 120
    
    # Discovery
    SEARCH_QUERIES: str = "Strategy Operations Analyst,Business Transformation Consultant,Management Consulting entry level"
    TARGET_LOCATIONS: str = "United States,Remote"
    MAX_JOBS_PER_CYCLE: int = 10
    CYCLES_PER_RUN: int = 10
    RECENCY_HOURS: int = 24
    
    # RPA
    HEADLESS_BROWSER: bool = True
    SCREENSHOT_ON_APPLY: bool = True
    SKIP_CUSTOM_QUESTIONS: bool = True
    APPLY_DELAY_SECONDS: int = 5  # delay between applications to avoid rate limits
    
    # Schedule
    RUN_TIMES: str = "08:00,18:00"  # 2x daily
    
    # Paths
    OUTPUT_DIR: str = "data/outputs"
    PROFILE_DIR: str = "data/profiles"
    TEMPLATE_DIR: str = "backend/templates"
    
    @property
    def search_query_list(self) -> List[str]:
        return [q.strip() for q in self.SEARCH_QUERIES.split(",")]
    
    @property
    def location_list(self) -> List[str]:
        return [l.strip() for l in self.TARGET_LOCATIONS.split(",")]
    
    @property
    def run_time_list(self) -> List[str]:
        return [t.strip() for t in self.RUN_TIMES.split(",")]
    
    class Config:
        env_file = ".env"

settings = Settings()

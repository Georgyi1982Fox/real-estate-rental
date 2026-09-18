from pathlib import Path

# Базовая директория проекта
BASE_DIR = Path(__file__).parent.parent.parent.parent

# LLM Settings
LLM_PROVIDER = "qwen"
LLM_API_KEY = ""
LLM_BASE_URL = "https://api.aitunnel.com/v1"  
LLM_MODEL = "qwen-max"

# Redis Settings
REDIS_URL = "redis://localhost:6379"

# Database URL (для совместимости с существующей БД)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/bina"
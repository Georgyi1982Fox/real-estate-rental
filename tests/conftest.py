import os
import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Устанавливаем переменные окружения для тестов
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_bina")
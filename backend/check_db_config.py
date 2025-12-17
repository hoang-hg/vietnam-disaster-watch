import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from app.settings import settings

print(f"Current DB URL: {settings.app_db_url}")

import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from app.main import app
    print("Backend import: SUCCESS")
    
    from app.cache import cache
    print(f"Cache manager initialized (Redis Available: {cache.redis_client is not None})")
    
    from app.database import engine
    print(f"Database engine: {engine.url.drivername}")
    print("Sanity check: PASSED")
except Exception as e:
    print(f"Sanity check: FAILED - {e}")
    sys.exit(1)

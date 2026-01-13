from slowapi import Limiter
from slowapi.util import get_remote_address

# Centralized rate limiter instance to avoid circular imports
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri="memory://"
)

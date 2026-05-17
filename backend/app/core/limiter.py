from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

# Inisialisasi limiter dengan Redis (jika ada) atau memory
# Untuk production gunakan Redis: storage_uri="redis://localhost:6379"
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

def setup_rate_limit(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
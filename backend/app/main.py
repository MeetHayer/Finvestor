import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.api.routes import router as data_router
from app.api.portfolios_watchlists import router as pw_router
from app.routes.portfolios import router as portfolios_router

app = FastAPI(title="Finvestor API")

# Strict, Safari-friendly CORS
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
# Add Vercel frontend URL from environment variable
if os.getenv("FRONTEND_URL"):
    ALLOWED_ORIGINS.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,        # explicit origins only
    allow_credentials=False,              # keep False unless you truly use cookies
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Tiny request logger
@app.middleware("http")
async def log_origin(request: Request, call_next):
    print(f"[CORS] {request.method} {request.url.path} ← Origin={request.headers.get('origin')}")
    resp: Response = await call_next(request)
    return resp

@app.get("/api/health")
async def health():
    return {"ok": True}

# Routers
app.include_router(data_router)
app.include_router(pw_router)
# The consolidated portfolio/watchlist API lives in app.api.portfolios_watchlists
# Avoid double-mounting conflicting portfolio routes
# app.include_router(portfolios_router)
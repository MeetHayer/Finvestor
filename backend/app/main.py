from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as data_router
from app.api.portfolios_watchlists import router as pw_router

app = FastAPI(title="Finvestor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Include both routers
app.include_router(data_router)  # Market data, search, health
app.include_router(pw_router)    # Portfolios and watchlists
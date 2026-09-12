from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, subscriptions, payments, predictions, affiliates
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Analytics Foot API",
    description="API du site de pronostics/analyses IA foot — Pass VIP + programme d'affiliation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(subscriptions.router)
app.include_router(payments.router)
app.include_router(predictions.router)
app.include_router(affiliates.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

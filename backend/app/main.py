"""
CloudSentinel — Zero-Day Threat Detection Platform
FastAPI backend entrypoint
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging

from app.config import settings
from app.api.threats import router as threats_router
from app.api.metrics import router as metrics_router
from app.api.websocket import router as ws_router
from app.ingest.kafka_consumer import start_kafka_consumer, stop_kafka_consumer
from app.ml.ensemble import EnsembleThreatScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloudsentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load ML models + start Kafka consumer."""
    logger.info("Loading ML models...")
    app.state.scorer = EnsembleThreatScorer()
    app.state.scorer.load_models(settings.MODEL_PATH)

    logger.info("Starting Kafka consumer...")
    await start_kafka_consumer(app)

    yield

    logger.info("Shutting down Kafka consumer...")
    await stop_kafka_consumer()


app = FastAPI(
    title="CloudSentinel API",
    description="Zero-Day Threat Detection for Cloud Infrastructure",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(threats_router, prefix="/api/v1/threats", tags=["threats"])
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
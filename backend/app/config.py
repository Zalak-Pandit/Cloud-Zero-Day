from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CloudSentinel"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/cloudsentinel"

    # Redis (for caching + pub/sub for WebSocket)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: List[str] = ["localhost:9092"]
    KAFKA_TOPIC_LOGS: str = "cloud-logs"
    KAFKA_TOPIC_NETWORK: str = "network-events"
    KAFKA_TOPIC_API: str = "api-events"
    KAFKA_CONSUMER_GROUP: str = "cloudsentinel-consumer"

    # ML
    MODEL_PATH: str = "./models"
    ANOMALY_THRESHOLD: float = 0.72   # score above this = threat
    CRITICAL_THRESHOLD: float = 0.90  # score above this = critical

    # AWS (for auto-quarantine)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Alerts
    SLACK_WEBHOOK_URL: str = ""
    PAGERDUTY_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
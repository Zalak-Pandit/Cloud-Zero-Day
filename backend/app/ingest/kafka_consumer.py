"""
Kafka consumer — reads cloud events from multiple topics,
pre-processes them, and routes them through the ML ensemble.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from kafka import KafkaConsumer
from fastapi import FastAPI

from app.config import settings
from app.ingest.log_parser import parse_log_event, parse_network_event, parse_api_event

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


async def start_kafka_consumer(app: FastAPI):
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop(app))


async def stop_kafka_consumer():
    if _consumer_task:
        _consumer_task.cancel()


async def _consume_loop(app: FastAPI):
    """Main consumption loop — runs in a background asyncio task."""
    loop = asyncio.get_event_loop()

    try:
        consumer = await loop.run_in_executor(None, _build_consumer)
    except Exception as e:
        logger.warning(f"Kafka not available ({e}) — running without live ingestion")
        return

    logger.info("Kafka consumer started")

    while True:
        try:
            # Poll in executor so we don't block the event loop
            messages = await loop.run_in_executor(None, lambda: consumer.poll(timeout_ms=100))
            for tp, records in messages.items():
                for record in records:
                    await _handle_record(app, tp.topic, record.value)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            await asyncio.sleep(1)

    consumer.close()


def _build_consumer() -> KafkaConsumer:
    topics = [
        settings.KAFKA_TOPIC_LOGS,
        settings.KAFKA_TOPIC_NETWORK,
        settings.KAFKA_TOPIC_API,
    ]
    return KafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )


TOPIC_TYPE_MAP = {
    settings.KAFKA_TOPIC_NETWORK: "network",
    settings.KAFKA_TOPIC_LOGS: "log",
    settings.KAFKA_TOPIC_API: "api",
}

PARSERS = {
    "network": parse_network_event,
    "log": parse_log_event,
    "api": parse_api_event,
}


async def _handle_record(app: FastAPI, topic: str, raw: Dict[str, Any]):
    """Parse → score → persist if threat detected."""
    from app.api.websocket import broadcast_event

    event_type = TOPIC_TYPE_MAP.get(topic, "network")
    parser = PARSERS[event_type]

    try:
        event = parser(raw)
        event["_type"] = event_type
    except Exception as e:
        logger.debug(f"Parse error on {topic}: {e}")
        return

    scorer = app.state.scorer
    threat = scorer.evaluate(event)

    if threat:
        from app.api.threats import persist_threat
        saved = await persist_threat(threat)

        # Broadcast to WebSocket clients
        await broadcast_event({
            "type": "new_threat",
            "threat": {
                "id": saved.id,
                "severity": saved.severity,
                "threat_type": saved.threat_type,
                "confidence_score": saved.confidence_score,
                "source_ip": saved.source_ip,
                "description": saved.description,
                "created_at": saved.created_at.isoformat(),
            },
        })

        # Auto-quarantine criticals
        if saved.severity in ("critical", "high") and saved.source_ip:
            from app.response.quarantine import auto_quarantine
            asyncio.create_task(auto_quarantine(saved))

        # Alert
        from app.response.alert import send_alert
        asyncio.create_task(send_alert(saved))
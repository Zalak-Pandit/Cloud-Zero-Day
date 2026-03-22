"""
Alert Router — sends threat notifications to Slack and PagerDuty.
"""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

PAGERDUTY_SEVERITY = {
    "critical": "critical",
    "high": "error",
    "medium": "warning",
    "low": "info",
}


async def send_alert(threat) -> None:
    if settings.SLACK_WEBHOOK_URL:
        await _send_slack(threat)
    if settings.PAGERDUTY_API_KEY and threat.severity in ("critical", "high"):
        await _send_pagerduty(threat)


async def _send_slack(threat) -> None:
    emoji = SEVERITY_EMOJI.get(threat.severity, "⚠️")
    payload = {
        "text": f"{emoji} *CloudSentinel Alert* — {threat.severity.upper()} threat detected",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{threat.severity.upper()} — {threat.threat_type.replace('_', ' ').title()}*\n"
                        f"*Source:* `{threat.source_ip or 'unknown'}`\n"
                        f"*Target:* `{threat.target_resource or 'unknown'}`\n"
                        f"*Confidence:* {threat.confidence_score:.0%}\n"
                        f"*Description:* {threat.description}"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Threat ID: `{threat.id}`  •  Region: `{threat.region or 'unknown'}`"}
                ],
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Slack alert failed: {e}")


async def _send_pagerduty(threat) -> None:
    payload = {
        "routing_key": settings.PAGERDUTY_API_KEY,
        "event_action": "trigger",
        "dedup_key": threat.id,
        "payload": {
            "summary": f"[{threat.severity.upper()}] {threat.threat_type} from {threat.source_ip}",
            "severity": PAGERDUTY_SEVERITY.get(threat.severity, "warning"),
            "source": threat.source_ip or "unknown",
            "custom_details": {
                "threat_id": threat.id,
                "confidence": threat.confidence_score,
                "description": threat.description,
                "indicators": threat.indicators,
                "model_scores": threat.model_scores,
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
            )
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"PagerDuty alert failed: {e}")
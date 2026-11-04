"""GitHub Webhook Delivery Ingestion, Signature Verification, and Idempotency Service."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import WebhookDelivery


class WebhookService:
    """Handles webhook verification, deduplication, and lifecycle tracking."""

    def __init__(self):
        self._memory_seen_deliveries: set[str] = set()

    def verify_signature(self, payload_bytes: bytes, signature_header: str | None) -> None:
        """Verifies HMAC SHA-256 webhook signature using GITHUB_WEBHOOK_SECRET.

        Never uses GITHUB_TOKEN as webhook secret.
        Rejects invalid signatures when provided, or when configured in production.
        """
        secret = (getattr(settings, "GITHUB_WEBHOOK_SECRET", "") or "").strip()
        if not secret:
            return

        if signature_header:
            expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature_header):
                logger.warning("Rejected webhook: Invalid HMAC SHA-256 signature.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )
        elif getattr(settings, "GITPULSE_ENV", "").lower() == "production":
            logger.warning("Rejected webhook: Missing signature header in production.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature header",
            )

    async def is_delivery_processed(self, delivery_id: str) -> bool:
        """Checks whether a webhook delivery has already been processed (idempotency check)."""
        if not delivery_id:
            return False

        if delivery_id in self._memory_seen_deliveries:
            return True

        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                stmt = select(WebhookDelivery.id).where(WebhookDelivery.delivery_id == delivery_id)
                res = await session.execute(stmt)
                if res.scalar_one_or_none() is not None:
                    self._memory_seen_deliveries.add(delivery_id)
                    return True
        except Exception as exc:
            logger.debug("Webhook delivery lookup warning: %s", exc)

        return False

    async def record_delivery(
        self,
        delivery_id: str,
        event_type: str,
        repo_github_id: int | None,
        repo_full_name: str | None,
        payload_bytes: bytes,
        sender_login: str | None,
    ) -> None:
        """Records a processed webhook delivery for audit and idempotency."""
        if not delivery_id:
            return

        self._memory_seen_deliveries.add(delivery_id)
        if len(self._memory_seen_deliveries) > 10000:
            # Avoid unbounded memory growth
            self._memory_seen_deliveries.clear()
            self._memory_seen_deliveries.add(delivery_id)

        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    delivery = WebhookDelivery(
                        delivery_id=delivery_id,
                        event_type=event_type,
                        repo_github_id=repo_github_id,
                        repo_full_name=repo_full_name,
                        payload_hash=hashlib.sha256(payload_bytes).hexdigest(),
                        sender_login=sender_login,
                        status="PROCESSED",
                        created_at=datetime.now(UTC),
                    )
                    session.add(delivery)
        except Exception as exc:
            logger.debug("Webhook delivery persistence note: %s", exc)


webhook_service = WebhookService()

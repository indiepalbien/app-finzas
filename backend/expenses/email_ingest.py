import logging
from datetime import date
from email.utils import parseaddr
from typing import Optional

from django.db import transaction, IntegrityError
from django.utils import timezone

from expenses.email_parsers.visa import parse_visa_alert
from expenses.models import (
    PendingTransaction,
    Source,
    Transaction as Tx,
    UserEmailMessage,
)


logger = logging.getLogger(__name__)


def _get_or_create_source(user, source_name: str) -> Optional[Source]:
    if not source_name:
        return None
    obj, _ = Source.objects.get_or_create(user=user, name=source_name)
    return obj


def process_new_messages() -> int:
    """Process unprocessed UserEmailMessage entries and create transactions or pending duplicates.

    Returns the count of processed messages.
    """
    qs = UserEmailMessage.objects.filter(processed_at__isnull=True)
    count = 0
    for msg in qs.iterator():
        parsed = None
        try:
            logger.info("📧 Processing email msg_id=%s subject='%s' user=%s", 
                       msg.message_id, msg.subject, msg.user_id)
            
            parsed = parse_visa_alert(bytes(msg.raw_eml))
            logger.info("✓ Parsed email msg_id=%s amount=%s currency=%s description='%s'",
                       msg.message_id, parsed.get("amount"), parsed.get("currency"), 
                       parsed.get("description", "")[:50])

            # Gate by sender: allow direct sender, forwarded, or body mention
            allowed_sender = "donotreplyalertadecomprasvisa@visa.com"
            envelope_from = parseaddr(msg.from_address or "")[1].lower()
            parsed_froms = parsed.get("from_emails") or []
            body = (parsed.get("raw_body") or "").lower()
            
            if not (
                envelope_from == allowed_sender
                or allowed_sender in parsed_froms
                or allowed_sender in body
            ):
                logger.warning(
                    "⚠️  SKIPPED msg_id=%s reason=sender_mismatch envelope_from=%s (expected %s)",
                    msg.message_id,
                    envelope_from,
                    allowed_sender,
                )
                msg.processing_error = "skipped_non_visa_sender"
                msg.processed_at = timezone.now()
                msg.save(update_fields=["processing_error", "processed_at"])
                continue
            if not parsed.get("amount") or not parsed.get("currency"):
                logger.warning(
                    "⚠️  SKIPPED msg_id=%s reason=missing_amount_currency amount=%s currency=%s",
                    msg.message_id,
                    parsed.get("amount"),
                    parsed.get("currency"),
                )
                msg.processing_error = "Missing amount or currency"
                msg.processed_at = timezone.now()
                msg.save(update_fields=["processing_error", "processed_at"])
                continue

            external_id = parsed.get("external_id")
            # if external_id already exists for user, push to pending
            exists = Tx.objects.filter(user=msg.user, external_id=external_id).exists() if external_id else False
            if exists:
                logger.warning(
                    "⚠️  DUPLICATE msg_id=%s external_id=%s → moved to pending",
                    msg.message_id,
                    external_id,
                )
                PendingTransaction.objects.create(
                    user=msg.user,
                    external_id=external_id or "",
                    payload=parsed,
                    reason="duplicate",
                )
                msg.processed_at = timezone.now()
                msg.save(update_fields=["processed_at"])
                count += 1
                continue

            with transaction.atomic():
                tx_date = msg.date.date() if msg.date else date.today()
                tx = Tx.objects.create(
                    user=msg.user,
                    date=tx_date,
                    description=parsed.get("description") or "",
                    amount=parsed.get("amount"),
                    currency=(parsed.get("currency") or "").upper(),
                    source=_get_or_create_source(msg.user, parsed.get("source")),
                    external_id=external_id,
                    status="confirmed",
                )
            logger.info(
                "✅ CREATED transaction id=%s amount=%s %s description='%s' (msg_id=%s)",
                tx.id,
                tx.amount,
                tx.currency,
                tx.description[:50],
                msg.message_id,
            )
            msg.processed_at = timezone.now()
            msg.save(update_fields=["processed_at"])
            count += 1
        except IntegrityError as exc:
            logger.warning(
                "⚠️  INTEGRITY ERROR msg_id=%s external_id=%s → moved to pending. Error: %s",
                msg.message_id,
                parsed.get("external_id") if parsed else None,
                str(exc)[:200],
            )
            if parsed:
                PendingTransaction.objects.create(
                    user=msg.user,
                    external_id=parsed.get("external_id") or "",
                    payload=parsed,
                    reason="duplicate",
                )
            msg.processed_at = timezone.now()
            msg.save(update_fields=["processed_at"])
            count += 1
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.error(
                "❌ FAILED processing msg_id=%s subject='%s' user=%s\n"
                "   Error: %s\n"
                "   Parsed data: %s",
                msg.message_id,
                msg.subject,
                msg.user_id,
                error_msg,
                parsed if parsed else "Failed to parse",
                exc_info=True
            )
            msg.processing_error = error_msg[:500]  # Limit error message length
            msg.processed_at = timezone.now()
            msg.save(update_fields=["processing_error", "processed_at"])
    return count

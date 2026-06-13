"""Domain models for operator-managed cheki records.

A cheki record captures the *metadata* of a cheki purchase/shoot (cast, visit,
type, quantity) so it can be reconciled against POS and counted per cast —
**the cheki image itself is never stored here** (image_stored is a flag only;
이미지 저장 안 해도 메타데이터는 기록, ASS-95). Settlement linkage is structural,
not a confirmed amount: ``settlement_status`` stays candidate/hold/excluded
because the settled value is a human-gated decision (Data 제약), so this domain
never writes a money figure.
"""

from __future__ import annotations

import uuid

from django.db import models

# Single café for Release 0.1 (see visit.models.DEFAULT_STORE_ID rationale).
DEFAULT_STORE_ID = "hatsukoi"


class ChekiType(models.TextChoices):
    """Cheki kind (Data_Event_Schema cheki_type domain)."""

    BASIC = "basic", "basic"
    OPTION = "option", "option"
    EVENT = "event", "event"
    COMP = "comp", "comp"
    TEST = "test", "test"


class ChekiSettlementStatus(models.TextChoices):
    """Settlement linkage state — never a confirmed amount.

    The settled value is human-gated (price/refund/settlement), so a record only
    declares whether it is a settlement *candidate*, on *hold* (needs review), or
    *excluded* (test/void/refund). The actual figure is decided elsewhere.
    """

    CANDIDATE = "candidate", "candidate"
    HOLD = "hold", "hold"
    EXCLUDED = "excluded", "excluded"


class ChekiRecordStatus(models.TextChoices):
    """Lifecycle for a cheki record that is never physically deleted."""

    ACTIVE = "active", "active"
    VOIDED = "voided", "voided"


class ChekiRecord(models.Model):
    """Operator-maintained cheki purchase/shoot metadata for reconciliation.

    Append-oriented like :class:`~apps.visit.models.VisitRecord`: rows are voided
    (not deleted) so the cheki-count vs sales reconciliation keeps the trail.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Conditional per Data_Event_Schema (cheki_recorded ids.fan_id 조건부): an
    # anonymous-visit cheki has no fan yet, so this is nullable.
    fan = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="cheki_records",
        null=True,
        blank=True,
    )
    visit = models.ForeignKey(
        "visit.VisitRecord",
        on_delete=models.PROTECT,
        related_name="cheki_records",
    )
    # cast_id is a plain identifier: the cast app is a P0 placeholder with no
    # model yet, so there is no FK target. Swap to a FK when cast lands.
    cast_id = models.CharField(max_length=64)
    cheki_type = models.CharField(max_length=16, choices=ChekiType.choices)
    quantity = models.PositiveIntegerField(default=1)
    # The cheki image is never persisted here; this only records whether one was
    # stored elsewhere (consent-scoped), per ASS-95.
    image_stored = models.BooleanField(default=False)
    consent_scope = models.CharField(max_length=32, blank=True, default="")
    settlement_status = models.CharField(
        max_length=16,
        choices=ChekiSettlementStatus.choices,
        default=ChekiSettlementStatus.CANDIDATE,
    )
    # Optional POS linkage (P0 manual; pos_order_id after POS confirmation).
    pos_order_id = models.CharField(max_length=64, blank=True, default="")
    pos_receipt_no = models.CharField(max_length=64, blank=True, default="")
    store_id = models.CharField(max_length=64, default=DEFAULT_STORE_ID)
    status = models.CharField(
        max_length=16,
        choices=ChekiRecordStatus.choices,
        default=ChekiRecordStatus.ACTIVE,
    )
    void_reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "identity.Account",
        on_delete=models.PROTECT,
        related_name="created_cheki_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["cast_id", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["settlement_status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Identify the cheki by cast and quantity for admin/log display."""
        return f"cheki:{self.id}:{self.cast_id}x{self.quantity}"

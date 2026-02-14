from django.db import transaction
from django.db.models import Sum
from .models import InventoryLedger, InventoryLot


def get_stock_summary(item):
    received = InventoryLedger.objects.filter(
        item=item, txnType="RECEIVE"
    ).aggregate(Sum("qty"))["qty__sum"] or 0

    issued = InventoryLedger.objects.filter(
        item=item, txnType="ISSUE"
    ).aggregate(Sum("qty"))["qty__sum"] or 0

    reserved = (
        InventoryLedger.objects.filter(item=item, txnType="RESERVE")
        .aggregate(Sum("qty"))["qty__sum"] or 0
    ) - (
        InventoryLedger.objects.filter(item=item, txnType="UNRESERVE")
        .aggregate(Sum("qty"))["qty__sum"] or 0
    )

    onHand = received - issued
    available = onHand - reserved

    return {
        "onHand": onHand,
        "reserved": reserved,
        "available": available,
    }


@transaction.atomic
def reserve_inventory(item, qty, idempotencyKey):
    if InventoryLedger.objects.filter(idempotencyKey=idempotencyKey).exists():
        return "IDEMPOTENT_REPLAY"

    summary = get_stock_summary(item)
    if summary["available"] < qty:
        raise Exception("INSUFFICIENT_STOCK")

    lot = InventoryLot.objects.filter(
        item=item, qcStatus="APPROVED"
    ).first()

    if not lot:
        raise Exception("NO_QC_APPROVED_LOT")

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="RESERVE",
        qty=qty,
        idempotencyKey=idempotencyKey,
    )


@transaction.atomic
def issue_inventory(item, qty, idempotencyKey):
    if InventoryLedger.objects.filter(idempotencyKey=idempotencyKey).exists():
        return "IDEMPOTENT_REPLAY"

    summary = get_stock_summary(item)
    if summary["reserved"] < qty:
        raise Exception("RESERVATION_NOT_FOUND")

    lot = InventoryLot.objects.filter(
        item=item, qcStatus="APPROVED"
    ).first()

    if not lot:
        raise Exception("NO_QC_APPROVED_LOT")

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="ISSUE",
        qty=qty,
        idempotencyKey=idempotencyKey,
    )

    InventoryLedger.objects.create(
        item=item,
        lot=lot,
        txnType="UNRESERVE",
        qty=qty,
        idempotencyKey=idempotencyKey + "_UNRESERVE",
    )

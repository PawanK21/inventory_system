from django.db import models
from django.utils import timezone

class Item(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    qcRequired = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class InventoryLot(models.Model):
    QC_STATUS = (
        ("APPROVED", "APPROVED"),
        ("QUARANTINE", "QUARANTINE"),
        ("REJECTED", "REJECTED"),
    )

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    lotCode = models.CharField(max_length=100)
    receivedQty = models.PositiveIntegerField()
    qcStatus = models.CharField(max_length=20, choices=QC_STATUS)

    def __str__(self):
        return f"{self.item.code} - {self.lotCode}"


class InventoryLedger(models.Model):
    TXN_TYPES = (
        ("RECEIVE", "RECEIVE"),
        ("RESERVE", "RESERVE"),
        ("UNRESERVE", "UNRESERVE"),
        ("ISSUE", "ISSUE"),
    )

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    lot = models.ForeignKey(InventoryLot, on_delete=models.CASCADE)
    txnType = models.CharField(max_length=20, choices=TXN_TYPES)
    qty = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    idempotencyKey = models.CharField(max_length=100, unique=True)

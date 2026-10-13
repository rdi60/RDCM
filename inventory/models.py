from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from scheduling.models import Appointment


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockLocation(models.Model):
    class LocationType(models.TextChoices):
        STORE = "store", "Central store"
        ROOM = "room", "Clinical room"

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=LocationType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["type", "name"], name="unique_stocklocation_type_name")
        ]

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, default="pcs", help_text="e.g. pcs, box, ml")
    reorder_level = models.PositiveIntegerField(
        default=0, help_text="Clinic-wide low-stock alert threshold. 0 = no alert."
    )
    track_expiry = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

    @property
    def total_quantity(self):
        total = self.stock_transactions.aggregate(total=Sum("quantity"))["total"]
        return total or 0

    @property
    def is_low_stock(self):
        return self.reorder_level > 0 and self.total_quantity < self.reorder_level


class StockBatch(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="batches")
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "created_at"]

    def __str__(self):
        return f"{self.item} ({self.batch_number})" if self.batch_number else str(self.item)

    def quantity_at(self, location):
        total = self.transactions.filter(location=location).aggregate(total=Sum("quantity"))["total"]
        return total or 0

    @property
    def quantity_remaining(self):
        total = self.transactions.aggregate(total=Sum("quantity"))["total"]
        return total or 0

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        return self.expiry_date <= date.today() + timezone.timedelta(days=60)

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < date.today())


class StockTransaction(models.Model):
    """
    The single ledger of every stock movement. Current quantity (per item,
    per location, per batch) is always computed by summing these signed
    rows — never a separately-maintained balance field — the same approach
    Invoice.paid_amount uses for payments, so there's nothing to drift out
    of sync.
    """

    class TxType(models.TextChoices):
        RECEIPT = "receipt", "Goods receipt"
        TRANSFER_OUT = "transfer_out", "Transfer out"
        TRANSFER_IN = "transfer_in", "Transfer in"
        CONSUMPTION = "consumption", "Consumption"
        ADJUSTMENT = "adjustment", "Adjustment"

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="stock_transactions")
    batch = models.ForeignKey(
        StockBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="transactions"
    )
    location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="stock_transactions")
    quantity = models.IntegerField(help_text="Positive for stock in, negative for stock out.")
    tx_type = models.CharField(max_length=15, choices=TxType.choices)
    reference = models.CharField(max_length=30, blank=True)
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_transactions"
    )
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_tx_type_display()} {self.quantity} {self.item} @ {self.location}"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to supplier"
        PARTIALLY_RECEIVED = "partially_received", "Partially received"
        RECEIVED = "received", "Fully received"
        CANCELLED = "cancelled", "Cancelled"

    po_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.po_number or f"Draft PO to {self.supplier}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.po_number:
            self.po_number = f"PO-{self.pk:05d}"
            super().save(update_fields=["po_number"])

    def send(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only a draft purchase order can be sent.")
        if not self.lines.exists():
            raise ValidationError("Add at least one line before sending.")
        self.status = self.Status.SENT
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        if self.status not in (self.Status.DRAFT, self.Status.SENT):
            raise ValidationError("Can't cancel a purchase order that has already received stock.")
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def recompute_status(self):
        if self.status not in (self.Status.SENT, self.Status.PARTIALLY_RECEIVED, self.Status.RECEIVED):
            return
        lines = list(self.lines.all())
        total_ordered = sum(line.quantity_ordered for line in lines)
        total_received = sum(line.quantity_received for line in lines)
        if total_received <= 0:
            self.status = self.Status.SENT
        elif total_received < total_ordered:
            self.status = self.Status.PARTIALLY_RECEIVED
        else:
            self.status = self.Status.RECEIVED
        self.save(update_fields=["status", "updated_at"])


class PurchaseOrderLine(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    quantity_ordered = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item} x{self.quantity_ordered}"

    @property
    def quantity_received(self):
        total = self.grn_lines.aggregate(total=Sum("quantity_received"))["total"]
        return total or 0

    @property
    def quantity_pending(self):
        return self.quantity_ordered - self.quantity_received


class GoodsReceiptNote(models.Model):
    grn_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="grns")
    location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="+")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    received_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return self.grn_number or f"GRN for {self.purchase_order}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.grn_number:
            self.grn_number = f"GRN-{self.pk:05d}"
            super().save(update_fields=["grn_number"])


class GoodsReceiptLine(models.Model):
    grn = models.ForeignKey(GoodsReceiptNote, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="grn_lines")
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity_received = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.po_line.item} x{self.quantity_received}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            batch = StockBatch.objects.create(
                item=self.po_line.item,
                batch_number=self.batch_number,
                expiry_date=self.expiry_date,
                cost_price=self.unit_cost,
            )
            StockTransaction.objects.create(
                item=self.po_line.item,
                batch=batch,
                location=self.grn.location,
                quantity=self.quantity_received,
                tx_type=StockTransaction.TxType.RECEIPT,
                reference=self.grn.grn_number,
                created_by=self.grn.received_by,
            )
            self.po_line.purchase_order.recompute_status()


class StockTransfer(models.Model):
    """One batch's movement from one location to another. A single transfer
    request for a quantity larger than one batch holds results in several
    of these (see inventory.services.fifo_consume) — each still records
    exactly which batch moved, which a single bigger row couldn't."""

    transfer_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="transfers")
    from_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="transfers_out")
    to_location = models.ForeignKey(StockLocation, on_delete=models.PROTECT, related_name="transfers_in")
    quantity = models.PositiveIntegerField()
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    transferred_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transferred_at"]

    def __str__(self):
        return self.transfer_number or f"Transfer of {self.batch}"

    def clean(self):
        if self.from_location_id and self.to_location_id and self.from_location_id == self.to_location_id:
            raise ValidationError("Source and destination must be different.")
        if self.batch_id and self.from_location_id and self.quantity:
            available = self.batch.quantity_at(self.from_location)
            if self.quantity > available:
                raise ValidationError(
                    f"Only {available} available at {self.from_location} for this batch."
                )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.transfer_number:
            self.transfer_number = f"TRF-{self.pk:05d}"
            super().save(update_fields=["transfer_number"])
        if is_new:
            StockTransaction.objects.create(
                item=self.batch.item,
                batch=self.batch,
                location=self.from_location,
                quantity=-self.quantity,
                tx_type=StockTransaction.TxType.TRANSFER_OUT,
                reference=self.transfer_number,
                created_by=self.transferred_by,
            )
            StockTransaction.objects.create(
                item=self.batch.item,
                batch=self.batch,
                location=self.to_location,
                quantity=self.quantity,
                tx_type=StockTransaction.TxType.TRANSFER_IN,
                reference=self.transfer_number,
                created_by=self.transferred_by,
            )

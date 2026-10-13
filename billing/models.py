from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from clinic.models import Treatment
from scheduling.models import Appointment, Patient

ZERO = Decimal("0.00")


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        PAID = "paid", "Paid"
        VOID = "void", "Void"

    invoice_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="invoices")
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=ZERO)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number or f"Draft invoice for {self.patient}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.invoice_number:
            self.invoice_number = f"INV-{self.pk:05d}"
            super().save(update_fields=["invoice_number"])

    @property
    def subtotal(self):
        total = self.line_items.aggregate(
            total=Sum(models.F("quantity") * models.F("unit_price"))
        )["total"]
        return total or ZERO

    @property
    def taxable_amount(self):
        return max(self.subtotal - self.discount, ZERO)

    @property
    def tax_amount(self):
        return (self.taxable_amount * self.tax_percent / Decimal("100")).quantize(ZERO)

    @property
    def total(self):
        return self.taxable_amount + self.tax_amount

    @property
    def paid_amount(self):
        total = self.payments.aggregate(total=Sum("amount"))["total"]
        return total or ZERO

    @property
    def balance_due(self):
        return self.total - self.paid_amount

    def recompute_status(self):
        """Call after any payment is added, changed or removed."""
        if self.status in (self.Status.DRAFT, self.Status.VOID):
            return
        if self.paid_amount <= ZERO:
            self.status = self.Status.ISSUED
        elif self.paid_amount < self.total:
            self.status = self.Status.PARTIALLY_PAID
        else:
            self.status = self.Status.PAID
        self.save(update_fields=["status", "updated_at"])

    def issue(self):
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only a draft invoice can be issued.")
        if not self.line_items.exists():
            raise ValidationError("Add at least one line item before issuing.")
        self.status = self.Status.ISSUED
        self.save(update_fields=["status", "updated_at"])

    def void(self):
        if self.status not in (self.Status.DRAFT, self.Status.ISSUED):
            raise ValidationError("Only a draft or unpaid issued invoice can be voided.")
        if self.paid_amount > ZERO:
            raise ValidationError("Can't void an invoice that already has payments recorded.")
        self.status = self.Status.VOID
        self.save(update_fields=["status", "updated_at"])


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    treatment = models.ForeignKey(
        Treatment, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Payment(models.Model):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        CHEQUE = "cheque", "Cheque"
        INSURANCE = "insurance", "Insurance"

    receipt_number = models.CharField(max_length=30, unique=True, blank=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=15, choices=Mode.choices)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return self.receipt_number or f"Payment for {self.invoice}"

    def clean(self):
        if self.amount is not None and self.amount <= ZERO:
            raise ValidationError("Payment amount must be greater than zero.")
        if self.invoice_id and self.invoice.status not in (
            Invoice.Status.ISSUED,
            Invoice.Status.PARTIALLY_PAID,
        ):
            raise ValidationError("Payments can only be recorded against an issued invoice.")
        if self.invoice_id and self.amount:
            already_paid = self.invoice.paid_amount
            if self.pk:
                already_paid -= Payment.objects.get(pk=self.pk).amount
            if already_paid + self.amount > self.invoice.total:
                raise ValidationError("This payment would exceed the invoice total.")

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.receipt_number:
            self.receipt_number = f"RCT-{self.pk:05d}"
            super().save(update_fields=["receipt_number"])
        self.invoice.recompute_status()

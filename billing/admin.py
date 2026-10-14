from django.contrib import admin

from .models import Invoice, InvoiceLineItem, Payment


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["receipt_number", "created_at"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceLineItemInline, PaymentInline]
    list_display = ["invoice_number", "patient", "status", "total", "paid_amount", "balance_due", "created_at"]
    list_filter = ["status"]
    search_fields = ["invoice_number", "patient__full_name", "patient__uhid"]
    readonly_fields = ["invoice_number", "created_by", "created_at", "updated_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "invoice", "amount", "mode", "paid_at", "received_by"]
    list_filter = ["mode"]
    search_fields = ["receipt_number", "invoice__invoice_number", "invoice__patient__full_name"]
    readonly_fields = ["receipt_number", "created_at"]

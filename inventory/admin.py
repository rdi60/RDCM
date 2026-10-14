from django.contrib import admin

from .models import (
    GoodsReceiptLine,
    GoodsReceiptNote,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    StockBatch,
    StockLocation,
    StockTransaction,
    StockTransfer,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "phone", "is_active"]
    search_fields = ["name", "contact_person", "phone"]


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "is_active"]
    list_filter = ["type", "is_active"]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "unit", "reorder_level", "total_quantity", "is_active"]
    list_filter = ["category", "is_active", "track_expiry"]
    search_fields = ["name", "category"]


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ["item", "batch_number", "expiry_date", "quantity_remaining", "cost_price"]
    list_filter = ["item"]
    search_fields = ["item__name", "batch_number"]
    readonly_fields = ["created_at"]


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ["created_at", "tx_type", "item", "location", "quantity", "reference"]
    list_filter = ["tx_type", "location"]
    search_fields = ["item__name", "reference"]
    readonly_fields = [f.name for f in StockTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ["transfer_number", "batch", "from_location", "to_location", "quantity", "transferred_at"]
    search_fields = ["transfer_number", "batch__item__name"]
    readonly_fields = [f.name for f in StockTransfer._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    inlines = [PurchaseOrderLineInline]
    list_display = ["po_number", "supplier", "status", "created_at"]
    list_filter = ["status", "supplier"]
    readonly_fields = ["po_number", "created_by", "created_at", "updated_at"]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0


@admin.register(GoodsReceiptNote)
class GoodsReceiptNoteAdmin(admin.ModelAdmin):
    inlines = [GoodsReceiptLineInline]
    list_display = ["grn_number", "purchase_order", "location", "received_at"]
    readonly_fields = ["grn_number", "received_by", "created_at"]

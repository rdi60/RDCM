from django.apps import AppConfig


# Every model whose rows are PHI or a financial record of a clinical/
# purchasing event. Master data (Doctor, Treatment, Specialty, Resource,
# StockLocation, Supplier, Item) is deliberately not tracked here — it's
# clinic configuration, not a patient or transaction record.
TRACKED_APP_MODELS = [
    ("scheduling", "Patient"),
    ("scheduling", "Appointment"),
    ("billing", "Invoice"),
    ("billing", "InvoiceLineItem"),
    ("billing", "Payment"),
    ("inventory", "PurchaseOrder"),
    ("inventory", "PurchaseOrderLine"),
    ("inventory", "GoodsReceiptNote"),
    ("inventory", "GoodsReceiptLine"),
    ("inventory", "StockTransaction"),
    ("inventory", "StockTransfer"),
]


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "Audit Log"

    def ready(self):
        from django.apps import apps
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
        from django.db.models.signals import post_delete, post_save

        from . import signals

        user_logged_in.connect(signals.log_login, dispatch_uid="audit_log_login")
        user_logged_out.connect(signals.log_logout, dispatch_uid="audit_log_logout")
        user_login_failed.connect(signals.log_login_failed, dispatch_uid="audit_log_login_failed")

        for app_label, model_name in TRACKED_APP_MODELS:
            model = apps.get_model(app_label, model_name)
            post_save.connect(signals.log_save, sender=model, dispatch_uid=f"audit_save_{app_label}_{model_name}")
            post_delete.connect(
                signals.log_delete, sender=model, dispatch_uid=f"audit_delete_{app_label}_{model_name}"
            )

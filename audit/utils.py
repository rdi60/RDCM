from .models import AuditLog


def get_client_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_view(request, instance):
    """Call from a detail view right after fetching a PHI-bearing object
    (Patient, Appointment, Invoice, ...). There's no Django signal for a
    read, so this is the one place audit logging has to be explicit rather
    than automatic."""
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=AuditLog.Action.VIEW,
        model_name=f"{instance._meta.app_label}.{instance._meta.model_name}",
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        ip_address=get_client_ip(request),
        path=request.path,
    )

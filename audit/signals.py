from .middleware import get_current_request
from .models import AuditLog
from .utils import get_client_ip


def _request_user(request):
    user = getattr(request, "user", None) if request else None
    if user is not None and not user.is_authenticated:
        user = None
    return user


def log_save(sender, instance, created, **kwargs):
    request = get_current_request()
    AuditLog.objects.create(
        user=_request_user(request),
        action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        model_name=f"{sender._meta.app_label}.{sender._meta.model_name}",
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        ip_address=get_client_ip(request),
        path=request.path if request else "",
    )


def log_delete(sender, instance, **kwargs):
    request = get_current_request()
    AuditLog.objects.create(
        user=_request_user(request),
        action=AuditLog.Action.DELETE,
        model_name=f"{sender._meta.app_label}.{sender._meta.model_name}",
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        ip_address=get_client_ip(request),
        path=request.path if request else "",
    )


def log_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGIN,
        ip_address=get_client_ip(request),
        path=request.path if request else "",
    )


def log_logout(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGOUT,
        ip_address=get_client_ip(request),
        path=request.path if request else "",
    )


def log_login_failed(sender, credentials, request=None, **kwargs):
    AuditLog.objects.create(
        user=None,
        username_attempted=credentials.get("username", "")[:150],
        action=AuditLog.Action.LOGIN_FAILED,
        ip_address=get_client_ip(request),
        path=request.path if request else "",
    )

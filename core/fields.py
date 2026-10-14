from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def get_fernet():
    """Public so data migrations can encrypt/decrypt existing rows with the
    exact same key and scheme EncryptedTextField itself uses."""
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY is not set — EncryptedTextField can't operate without it. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode("ascii") if isinstance(key, str) else key)


class EncryptedTextField(models.TextField):
    """
    Field-level encryption at rest (HIPAA 164.312(a)(2)(iv)) for a single
    free-text column, using Fernet (AES-128-CBC + HMAC) from `cryptography`.
    The key lives only in FIELD_ENCRYPTION_KEY (environment), never in the
    database or source control — see .env.example.

    This trades away the ability to filter, order, or search on the field at
    the database level: ciphertext is opaque and non-deterministic (a fresh
    random IV every save), so equal plaintext never produces equal
    ciphertext. That's an inherent cost of real encryption, not an
    oversight — use this only for fields nothing needs to query by value
    (Patient.medical_history, Appointment.notes), never for anything
    filtered, ordered, or searched on.
    """

    description = "Text encrypted at rest with Fernet"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return get_fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return get_fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise InvalidToken(
                f"Could not decrypt a value in {self.model.__name__}.{self.name} — "
                "FIELD_ENCRYPTION_KEY doesn't match the key this row was encrypted with."
            ) from exc

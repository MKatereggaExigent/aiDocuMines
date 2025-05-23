import base64
import os
from django.db import models
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def fix_b64_padding(b64_string):
    """Ensure proper base64 padding for decoding."""
    return b64_string + '=' * (-len(b64_string) % 4)


class EncryptedCharField(models.CharField):
    """
    Custom field that transparently encrypts/decrypts CharField data using AES-GCM.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        key_b64 = os.getenv("ENCRYPTION_SECRET_KEY")
        if not key_b64:
            raise ValueError("Missing ENCRYPTION_SECRET_KEY in environment")

        try:
            key_b64 = fix_b64_padding(key_b64)
            self._key = base64.urlsafe_b64decode(key_b64)
            self._aesgcm = AESGCM(self._key)
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_SECRET_KEY: {str(e)}")

    def get_prep_value(self, value):
        if value is None:
            return value
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, value.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            raw = base64.b64decode(value)
            nonce = raw[:12]
            encrypted = raw[12:]
            return self._aesgcm.decrypt(nonce, encrypted, None).decode()
        except Exception:
            return value  # fallback for corrupted/malformed data

    def to_python(self, value):
        if value is None or isinstance(value, str):
            try:
                raw = base64.b64decode(value)
                nonce = raw[:12]
                encrypted = raw[12:]
                return self._aesgcm.decrypt(nonce, encrypted, None).decode()
            except Exception:
                return value  # assume already decrypted or plaintext
        return value


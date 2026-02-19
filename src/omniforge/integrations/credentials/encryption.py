"""Credential encryption using Fernet symmetric encryption.

This module provides simple, secure encryption for OAuth tokens and credentials
using Fernet (symmetric encryption). For MVP, a single encryption key is used
from environment variables. Phase 2+ will migrate to per-tenant keys via AWS KMS.
"""

from cryptography.fernet import Fernet


class CredentialEncryption:
    """Simple Fernet encryption for credentials.

    MVP: Single key stored in environment variable.
    Phase 2+: Per-tenant keys via AWS KMS.

    Example:
        >>> key = Fernet.generate_key()
        >>> encryptor = CredentialEncryption(key)
        >>> encrypted = encryptor.encrypt("my_secret_token")
        >>> decrypted = encryptor.decrypt(encrypted)
        >>> assert decrypted == "my_secret_token"
    """

    def __init__(self, key: bytes) -> None:
        """Initialize encryption with a Fernet key.

        Args:
            key: Fernet encryption key (32 url-safe base64-encoded bytes)
        """
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt credential string to bytes.

        Args:
            plaintext: Credential to encrypt

        Returns:
            Encrypted credential as bytes
        """
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt credential bytes to string.

        Args:
            ciphertext: Encrypted credential bytes

        Returns:
            Decrypted credential string
        """
        return self._fernet.decrypt(ciphertext).decode()


def generate_encryption_key() -> bytes:
    """Generate a new Fernet encryption key.

    Run once at deployment, store in CREDENTIAL_ENCRYPTION_KEY env var.

    Returns:
        32 url-safe base64-encoded bytes suitable for Fernet encryption

    Example:
        >>> key = generate_encryption_key()
        >>> print(key.decode())  # Store this in CREDENTIAL_ENCRYPTION_KEY
    """
    return Fernet.generate_key()

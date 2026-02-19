"""Tests for credential encryption."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from omniforge.integrations.credentials.encryption import (
    CredentialEncryption,
    generate_encryption_key,
)


class TestCredentialEncryption:
    """Tests for CredentialEncryption class."""

    def test_generate_encryption_key_returns_bytes(self) -> None:
        """Generated key should be bytes."""
        key = generate_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_generate_encryption_key_returns_different_keys(self) -> None:
        """Multiple calls should return different keys."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        assert key1 != key2

    def test_encrypt_returns_bytes(self) -> None:
        """Encryption should return bytes."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = "my_secret_token"

        encrypted = encryptor.encrypt(plaintext)

        assert isinstance(encrypted, bytes)
        assert encrypted != plaintext.encode()

    def test_decrypt_returns_original_string(self) -> None:
        """Decryption should return original plaintext."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = "my_secret_token"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_with_special_characters(self) -> None:
        """Should handle special characters correctly."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = "token!@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_with_unicode(self) -> None:
        """Should handle unicode characters correctly."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = "token_with_emoji_🔒_and_中文"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_decrypt_with_wrong_key_raises_error(self) -> None:
        """Decrypting with wrong key should raise InvalidToken."""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        encryptor1 = CredentialEncryption(key1)
        encryptor2 = CredentialEncryption(key2)

        encrypted = encryptor1.encrypt("secret")

        with pytest.raises(InvalidToken):
            encryptor2.decrypt(encrypted)

    def test_decrypt_with_tampered_data_raises_error(self) -> None:
        """Decrypting tampered data should raise InvalidToken."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)

        encrypted = encryptor.encrypt("secret")
        tampered = encrypted[:-1] + b"X"

        with pytest.raises(InvalidToken):
            encryptor.decrypt(tampered)

    def test_encrypt_empty_string(self) -> None:
        """Should handle empty string correctly."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = ""

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_long_string(self) -> None:
        """Should handle long strings correctly."""
        key = Fernet.generate_key()
        encryptor = CredentialEncryption(key)
        plaintext = "x" * 10000

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

"""AES-256 encryption for captured data at rest."""

import base64
import hashlib
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DataEncryptor:
    """Encrypts and decrypts captured data using AES-256 via Fernet.

    All screenshots and analysis data are encrypted before being written to disk.
    The encryption key is derived from a user-provided passphrase using PBKDF2.
    """

    SALT_SIZE = 16
    KDF_ITERATIONS = 600_000

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._key_file = self._data_dir / ".keystore"
        self._fernet: Fernet | None = None

    def initialize(self, passphrase: str) -> None:
        """Derive encryption key from passphrase and store salt."""
        if self._key_file.exists():
            salt = self._key_file.read_bytes()
        else:
            salt = secrets.token_bytes(self.SALT_SIZE)
            self._key_file.write_bytes(salt)
            # Restrict file permissions (owner-only)
            self._key_file.chmod(0o600)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data. Returns ciphertext with embedded timestamp."""
        if self._fernet is None:
            raise RuntimeError("Encryptor not initialized — call initialize() first")
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt previously encrypted data."""
        if self._fernet is None:
            raise RuntimeError("Encryptor not initialized — call initialize() first")
        return self._fernet.decrypt(token)

    def encrypt_file(self, source: Path, dest: Path | None = None) -> Path:
        """Encrypt a file in place (or to dest). Original is securely deleted."""
        dest = dest or source.with_suffix(source.suffix + ".enc")
        plaintext = source.read_bytes()
        ciphertext = self.encrypt(plaintext)
        dest.write_bytes(ciphertext)
        dest.chmod(0o600)
        # Securely overwrite original before deleting
        _secure_delete(source)
        return dest

    def decrypt_file(self, source: Path) -> bytes:
        """Decrypt a file and return its contents (does not write to disk)."""
        return self.decrypt(source.read_bytes())


def _secure_delete(path: Path) -> None:
    """Overwrite file contents with random data before unlinking."""
    size = path.stat().st_size
    with open(path, "wb") as f:
        f.write(secrets.token_bytes(size))
        f.flush()
        os.fsync(f.fileno())
    path.unlink()

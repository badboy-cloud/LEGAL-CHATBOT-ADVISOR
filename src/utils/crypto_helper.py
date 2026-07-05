import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Retrieve key or use fallback for testing/initialization
# In production, this MUST be set in .env
_KEY = os.getenv("ENCRYPTION_KEY")
if not _KEY:
    # Generate a temporary key for safety in case of missing env
    _KEY = Fernet.generate_key().decode()

_fernet = Fernet(_KEY.encode())

def encrypt_data(data: bytes) -> bytes:
    """
    Encrypt raw bytes using AES-256 (via Fernet).
    """
    if not data:
        return b""
    return _fernet.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    """
    Decrypt raw bytes using AES-256 (via Fernet).
    """
    if not data:
        return b""
    return _fernet.decrypt(data)

def encrypt_string(text: str) -> str:
    """
    Encrypt a string and return a base64 encoded string.
    """
    if not text:
        return ""
    encrypted_bytes = _fernet.encrypt(text.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_string(enc_text: str) -> str:
    """
    Decrypt a base64 encoded string and return the plaintext string.
    """
    if not enc_text:
        return ""
    decrypted_bytes = _fernet.decrypt(enc_text.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")

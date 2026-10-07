import hashlib
import base64

from dilithium_py.ml_dsa import ML_DSA_65

ALGORITHM = "ML-DSA-65"
HASH_ALGORITHM = "SHA-256"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_keypair():
    public_key, secret_key = ML_DSA_65.keygen()
    return public_key, secret_key


def sign_hash(secret_key: bytes, document_hash_hex: str) -> bytes:
    message = bytes.fromhex(document_hash_hex)
    return ML_DSA_65.sign(secret_key, message)


def verify_hash(public_key: bytes, document_hash_hex: str, signature: bytes) -> bool:
    message = bytes.fromhex(document_hash_hex)

    try:
        return ML_DSA_65.verify(public_key, message, signature)
    except Exception:
        return False


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))

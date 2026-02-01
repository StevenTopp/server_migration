import secrets
import hashlib

def hash_password(password: str, salt: str = None) -> (str, str):
    if not salt:
        salt = secrets.token_hex(8)
    # 使用 pbkdf2 进行简单的哈希
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return pwd_hash, salt

def verify_password(stored_hash, stored_salt, provided_password):
    pwd_hash, _ = hash_password(provided_password, stored_salt)
    return secrets.compare_digest(pwd_hash, stored_hash)

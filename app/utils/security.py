from passlib.hash import pbkdf2_sha256

def hash_password(plain: str) -> str:
    # 29000 iteraciones por defecto, sal aleatoria; seguro y sin límite de 72 bytes
    return pbkdf2_sha256.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(plain, hashed)

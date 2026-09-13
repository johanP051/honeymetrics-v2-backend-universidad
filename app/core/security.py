from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto") # crea un admin de contrasenas llamado pwd_context y se configura para generar y verificar hashes usando Argon2

def hash_password(password: str) -> str:
    hashed_password = pwd_context.hash(password)
    return hashed_password

def verify_password(password: str, hashed_password: str) -> bool:
    passwd_validation = pwd_context.verify(password, hashed_password)
    return passwd_validation
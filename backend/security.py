import os
from datetime import datetime, timedelta, timezone
from typing import Union, Any
from dotenv import load_dotenv

# JWT Imports
from jose import jwt, JWTError
# Password Hashing Imports
from passlib.context import CryptContext
# AES Encryption Imports (Using Fernet which uses AES-128-CBC + HMAC, highly secure)
from cryptography.fernet import Fernet

# লোড এনভায়রনমেন্ট ভেরিয়েবল
load_dotenv()

# ==========================================
# 1. CONFIGURATIONS (from .env)
# ==========================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32 or SECRET_KEY.startswith("CHANGE_ME"):
    raise ValueError("JWT_SECRET_KEY is missing or too weak. Generate one: python -c \"import secrets; print(secrets.token_hex(32))\"")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # default 1 day

# AES Encryption Key (Must be 32 url-safe base64-encoded bytes)
ENCRYPTION_KEY = os.getenv("AES_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("AES_ENCRYPTION_KEY is not set in the .env file")

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# 2. PASSWORD HASHING
# ==========================================

def get_password_hash(password: str) -> str:
    """Converts a plain password into a secure bcrypt hash."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the provided password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==========================================
# 3. JWT TOKEN MANAGEMENT
# ==========================================

def create_access_token(subject: Union[str, Any], role: str, expires_delta: timedelta = None) -> str:
    """
    Creates a JWT access token for the user.
    'subject' is usually the user_id.
    'role' is 'USER' or 'ADMIN'.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "type": "access",
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, expected_type: str = "access") -> dict:
    """
    Decodes the JWT token and verifies its signature, expiration and purpose.
    Returns the payload if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def create_email_verification_token(user_id: Any) -> str:
    """Short-lived (48h) token used only for email verification links."""
    expire = datetime.now(timezone.utc) + timedelta(hours=48)
    return jwt.encode({"exp": expire, "sub": str(user_id), "type": "email_verify"}, SECRET_KEY, algorithm=ALGORITHM)


# ==========================================
# 4. AES ENCRYPTION FOR BINANCE API KEYS
# ==========================================

def encrypt_data(data: str) -> str:
    """
    Encrypts sensitive text (like Binance API Key) before saving to DB.
    """
    if not data:
        return ""
    encoded_data = data.encode('utf-8')
    encrypted_data = cipher_suite.encrypt(encoded_data)
    return encrypted_data.decode('utf-8')

def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypts the data retrieved from DB to use it for API calls.
    """
    if not encrypted_data:
        return ""
    encoded_data = encrypted_data.encode('utf-8')
    decrypted_data = cipher_suite.decrypt(encoded_data)
    return decrypted_data.decode('utf-8')
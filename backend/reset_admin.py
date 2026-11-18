"""
Reset (or create) the admin login.

    python reset_admin.py                     -> uses ADMIN_EMAIL / ADMIN_PASSWORD from .env
    python reset_admin.py me@mail.com NewPass@12345

Password must be at least 12 characters.
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, engine
from models import Base, User, UserRole, Wallet
from security import get_password_hash

email = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("ADMIN_EMAIL", "")).strip().lower()
pw = (sys.argv[2] if len(sys.argv) > 2 else os.getenv("ADMIN_PASSWORD", "")).strip()
if not email or len(pw) < 12:
    sys.exit("Need an email and a password of at least 12 characters (set ADMIN_EMAIL / ADMIN_PASSWORD in .env, or pass them as arguments).")

Base.metadata.create_all(bind=engine)
db = SessionLocal()
u = db.query(User).filter(User.email == email).first()
if u:
    u.password_hash, u.role, u.is_active, u.is_verified = get_password_hash(pw), UserRole.ADMIN, True, True
    print(f"Password reset for existing user {email} (now ADMIN).")
else:
    u = User(full_name="Super Admin", email=email, password_hash=get_password_hash(pw), role=UserRole.ADMIN, is_verified=True, is_active=True)
    db.add(u); db.flush(); db.add(Wallet(user_id=u.id))
    print(f"Admin created: {email}")
db.commit()
print("Done. Log in at /login")

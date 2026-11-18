import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from legal import TERMS_VERSION
from limiter import limiter, client_ip
from models import User, Wallet, UserRole, ConsentLog
from schemas import UserCreate, UserLogin, Token
from security import (
    get_password_hash, verify_password, create_access_token, verify_token,
    create_email_verification_token,
)

router = APIRouter()

# This tells FastAPI where to look for the token (in the Header)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ==========================================
# HELPERS
# ==========================================

def record_consent(db: Session, user: User, request: Request, consent_type: str, action: str, version: str):
    """Writes an immutable consent record (who / when / which version / from where)."""
    db.add(ConsentLog(
        user_id=user.id,
        consent_type=consent_type,
        action=action,
        version=version,
        ip_address=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    ))


# ==========================================
# 1. USER REGISTRATION (SIGNUP)
# ==========================================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    # 0. Terms must be accepted (checkbox) - enforced on the server, not only in the UI
    if not user_data.accepted_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the Terms & Conditions, Privacy Policy and Risk Disclosure to create an account."
        )
    if user_data.terms_version != TERMS_VERSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Terms have been updated. Please reload the page and accept the latest version."
        )

    email = user_data.email.lower().strip()

    # 1. Check if email already exists
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 2. Create user (trading permission is OFF until the user turns it on separately)
    now = datetime.now(timezone.utc)
    referrer = None
    if user_data.ref:
        referrer = db.query(User).filter(User.referral_code == user_data.ref.strip()).first()
    new_user = User(
        referred_by=referrer.id if referrer else None,
        full_name=user_data.full_name.strip(),
        email=email,
        password_hash=get_password_hash(user_data.password),
        role=UserRole.USER,
        is_verified=not REQUIRE_EMAIL_VERIFICATION,
        accepted_terms_at=now,
        terms_version=TERMS_VERSION,
        trading_consent=False,
    )
    db.add(new_user)
    db.flush()

    # 3. Wallet + consent record
    db.add(Wallet(user_id=new_user.id, real_balance=0, bonus_balance=0, spin_balance=0, total_earned=0))
    record_consent(db, new_user, request, "TERMS", "ACCEPT", TERMS_VERSION)
    db.commit()
    db.refresh(new_user)

    # 4. Email verification (optional, controlled by REQUIRE_EMAIL_VERIFICATION)
    if REQUIRE_EMAIL_VERIFICATION:
        try:
            from services.email import send_email
            link = f"{FRONTEND_URL}/api/backend/auth/verify-email?token={create_email_verification_token(new_user.id)}"
            send_email(
                new_user.email,
                "Verify your email",
                f'<p>Hi {new_user.full_name},</p><p>Please confirm your email: <a href="{link}">Verify email</a></p>'
                f'<p>The link expires in 48 hours.</p>',
            )
        except Exception:
            pass
        return {"access_token": "", "token_type": "bearer", "verification_required": True}

    access_token = create_access_token(subject=new_user.id, role=new_user.role.value)
    return {"access_token": access_token, "token_type": "bearer", "verification_required": False}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token, expected_type="email_verify")
    if not payload:
        return RedirectResponse(f"{FRONTEND_URL}/login?verified=0")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user:
        user.is_verified = True
        db.commit()
    return RedirectResponse(f"{FRONTEND_URL}/login?verified=1")


# ==========================================
# 2. USER LOGIN
# ==========================================

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login_user(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email.lower().strip()).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )

    if REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in.")

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return {"access_token": access_token, "token_type": "bearer", "verification_required": False}


# ==========================================
# 3. DEPENDENCIES (PROTECTING ROUTES)
# ==========================================

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have enough permissions to access this resource"
        )
    return current_user


def require_trading_consent(current_user: User = Depends(get_current_user)) -> User:
    """
    Server-side trading gate. Every endpoint that can place a trade MUST depend on this.
    A trade is allowed ONLY if the user has:
      1. accepted the CURRENT Terms version, and
      2. explicitly turned trading permission ON (and not revoked it).
    """
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Account is frozen. Trading is disabled.")
    if current_user.terms_version != TERMS_VERSION:
        raise HTTPException(status_code=403, detail="TERMS_OUTDATED: Please accept the updated Terms to continue trading.")
    if not current_user.trading_consent or current_user.trading_consent_version != TERMS_VERSION:
        raise HTTPException(status_code=403, detail="TRADING_CONSENT_REQUIRED: You have not given permission to trade.")
    return current_user

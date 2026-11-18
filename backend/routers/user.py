from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
import secrets, shutil, os
from datetime import datetime, timezone

from database import get_db
from legal import TERMS_VERSION
from limiter import limiter
from models import (
    User, Wallet, DashboardWidget, AppConfig, Transaction, TradingSignal, Airdrop,
)
from schemas import (
    UserResponse, WalletResponse, DashboardWidgetResponse, SignalResponse, AirdropResponse,
    SpinResponse, TradingConsentRequest, ConsentStatus, WithdrawRequestBody,
)
from auth import get_current_user, record_consent
from security import verify_password, get_password_hash
from pydantic import BaseModel, Field

router = APIRouter()

DEFAULT_PRIZES = [0.001, 0.002, 0.005, 0.008, 0.01, 0.0, 0.003, 0.004]
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def mask_name(name: str) -> str:
    name = (name or "?").strip()
    if len(name) <= 2:
        return name[:1] + "***"
    return name[0] + "***" + name[-1]


def _setting(db: Session, key: str, default):
    c = db.query(AppConfig).filter(AppConfig.config_key == key).first()
    return c.config_value if c else default


# ==========================================
# PROFILE / WALLET
# ==========================================

@router.get("/profile", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/wallet", response_model=WalletResponse)
def get_user_wallet(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.post("/upload-avatar")
def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if not (file.content_type or "").startswith("image/") or ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="File must be a JPG, PNG, WEBP or GIF image")
    data = file.file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Image must be smaller than 2MB")
    os.makedirs("static/avatars", exist_ok=True)
    filename = f"user_{current_user.id}_{secrets.token_hex(4)}.{ext}"
    with open(f"static/avatars/{filename}", "wb") as buffer:
        buffer.write(data)
    current_user.avatar_url = f"/static/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": current_user.avatar_url}


@router.get("/widgets", response_model=List[DashboardWidgetResponse])
def get_dashboard_widgets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(DashboardWidget).filter(DashboardWidget.is_active == True).order_by(DashboardWidget.display_order.asc()).all()


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


@router.put("/change-password")
def change_password(body: ChangePasswordBody, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


# ==========================================
# LEGAL CONSENT + TRADING PERMISSION
# ==========================================

def _consent_status(user: User) -> dict:
    terms_ok = user.terms_version == TERMS_VERSION
    trading_ok = bool(user.trading_consent) and user.trading_consent_version == TERMS_VERSION
    return {
        "current_terms_version": TERMS_VERSION,
        "accepted_terms_version": user.terms_version,
        "terms_up_to_date": terms_ok,
        "trading_consent": trading_ok,
        "trading_consent_at": user.trading_consent_at,
        "can_trade": terms_ok and trading_ok and not user.is_frozen,
    }


@router.get("/consent", response_model=ConsentStatus)
def get_consent_status(current_user: User = Depends(get_current_user)):
    return _consent_status(current_user)


@router.post("/consent/accept-terms", response_model=ConsentStatus)
def accept_updated_terms(request: Request, body: TradingConsentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Used when the Terms version changes and an existing user must accept the new version."""
    if not body.accepted or body.version != TERMS_VERSION:
        raise HTTPException(status_code=400, detail="You must accept the current Terms version.")
    current_user.terms_version = TERMS_VERSION
    current_user.accepted_terms_at = datetime.now(timezone.utc)
    record_consent(db, current_user, request, "TERMS", "ACCEPT", TERMS_VERSION)
    db.commit()
    return _consent_status(current_user)


@router.post("/trading-consent", response_model=ConsentStatus)
def set_trading_consent(request: Request, body: TradingConsentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    accepted=true  -> user gives permission for trading using their connected Binance account.
    accepted=false -> user revokes permission; no new trade can be placed afterwards.
    """
    now = datetime.now(timezone.utc)
    if body.accepted:
        if body.version != TERMS_VERSION:
            raise HTTPException(status_code=400, detail="Terms updated. Please reload and accept the latest version.")
        if current_user.terms_version != TERMS_VERSION:
            raise HTTPException(status_code=403, detail="TERMS_OUTDATED: Accept the updated Terms first.")
        current_user.trading_consent = True
        current_user.trading_consent_at = now
        current_user.trading_consent_version = TERMS_VERSION
        record_consent(db, current_user, request, "TRADING", "ACCEPT", TERMS_VERSION)
    else:
        current_user.trading_consent = False
        current_user.auto_trade_active = False
        record_consent(db, current_user, request, "TRADING", "REVOKE", TERMS_VERSION)
    db.commit()
    return _consent_status(current_user)


class FeedOptIn(BaseModel):
    show: bool


@router.put("/feed-opt-in")
def set_feed_opt_in(body: FeedOptIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.show_in_feed = body.show
    db.commit()
    return {"show_in_feed": current_user.show_in_feed}


# ==========================================
# PUBLIC ACTIVITY (REAL, OPT-IN ONLY)
# ==========================================

@router.get("/live-ticker")
def get_live_ticker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Real referral earnings of users who opted in. Names are masked. Nothing is invented."""
    rows = (
        db.query(Transaction, User)
        .join(User, User.id == Transaction.user_id)
        .filter(
            Transaction.transaction_type == "REFERRAL_COMMISSION",
            Transaction.status == "SUCCESS",
            User.show_in_feed == True,
        )
        .order_by(Transaction.created_at.desc())
        .limit(15)
        .all()
    )
    return [{"text": f"{mask_name(u.full_name)} earned ${float(t.amount):.2f}", "time": t.created_at, "type": "real"} for t, u in rows]


@router.get("/leaderboard")
def get_leaderboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Top real earners among users who opted in to be shown."""
    rows = (
        db.query(User, Wallet)
        .join(Wallet, Wallet.user_id == User.id)
        .filter(User.show_in_feed == True, User.is_active == True, Wallet.total_earned > 0)
        .order_by(Wallet.total_earned.desc())
        .limit(5)
        .all()
    )
    return [{"name": mask_name(u.full_name), "profit": float(w.total_earned), "rank": i + 1} for i, (u, w) in enumerate(rows)]


@router.get("/announcements")
def get_announcements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Announcements written by admins (Admin > Announcements)."""
    value = _setting(db, "ANNOUNCEMENTS", {"items": []})
    return value.get("items", []) if isinstance(value, dict) else []


# ==========================================
# SIGNALS
# ==========================================

@router.get("/signals", response_model=List[SignalResponse])
def get_trading_signals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(TradingSignal).filter(TradingSignal.status == "ACTIVE").order_by(TradingSignal.created_at.desc()).limit(1000).all()


# ==========================================
# DAILY SPIN (all segments equally likely - shown to the user)
# ==========================================

@router.get("/spin-prizes")
def get_spin_prizes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    prizes = _setting(db, "SPIN_PRIZES", DEFAULT_PRIZES)
    return prizes if isinstance(prizes, list) and prizes else DEFAULT_PRIZES


@router.post("/spin", response_model=SpinResponse)
@limiter.limit("20/minute")
def daily_spin(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    if current_user.last_spin_at and current_user.last_spin_at.date() == now.date():
        raise HTTPException(status_code=400, detail="Already spun today. Come back tomorrow!")

    prizes = _setting(db, "SPIN_PRIZES", DEFAULT_PRIZES)
    if not isinstance(prizes, list) or not prizes:
        prizes = DEFAULT_PRIZES

    index = secrets.randbelow(len(prizes))   # every segment has the same probability: 1 / len(prizes)
    reward = float(prizes[index])

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).with_for_update().first()
    if wallet:
        wallet.spin_balance = float(wallet.spin_balance) + reward
    current_user.last_spin_at = now
    db.commit()

    return {"success": True, "reward_amount": reward, "prize_index": index, "message": "Spin successful!"}


# ==========================================
# WITHDRAWALS (request -> admin review -> payout)
# ==========================================

@router.post("/withdraw")
@limiter.limit("10/minute")
def request_withdraw(request: Request, body: WithdrawRequestBody, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Creates a PENDING withdrawal and holds the amount. Funds are only paid out after an admin approves.
    If the admin rejects, the held amount is returned to the user's wallet.
    """
    if current_user.is_frozen:
        raise HTTPException(status_code=403, detail="Account is frozen. Please contact support.")

    from routers.setup import get_profile
    rules = get_profile(db)   # saved setup values, or safe defaults
    min_withdrawal = float(rules["min_withdrawal"])
    max_withdrawal = float(rules["max_withdrawal"] or 0)
    daily_limit = float(rules["daily_withdraw_limit"] or 0)
    amount = round(body.amount, 2)
    if amount < min_withdrawal:
        raise HTTPException(status_code=400, detail=f"Minimum withdrawal is ${min_withdrawal:.2f}")
    if max_withdrawal and amount > max_withdrawal:
        raise HTTPException(status_code=400, detail=f"Maximum withdrawal per request is ${max_withdrawal:.2f}")
    if daily_limit:
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        used = sum(float(t.amount) for t in db.query(Transaction).filter(
            Transaction.user_id == current_user.id, Transaction.transaction_type == "WITHDRAW",
            Transaction.status.in_(["PENDING", "SUCCESS"]), Transaction.created_at >= since).all())
        if used + amount > daily_limit:
            raise HTTPException(status_code=400, detail=f"Daily withdrawal limit is ${daily_limit:.2f}. Remaining today: ${max(daily_limit - used, 0):.2f}")
    fee = round(amount * float(rules["withdraw_fee_percent"]) / 100 + float(rules["withdraw_fee_flat"]), 2)
    if fee >= amount:
        raise HTTPException(status_code=400, detail="Amount is too small to cover the withdrawal fee.")

    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).with_for_update().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if float(wallet.real_balance) >= amount:
        wallet.real_balance = float(wallet.real_balance) - amount
        source = "real"
    elif float(wallet.spin_balance) >= amount:
        if not current_user.has_deposited:
            raise HTTPException(status_code=400, detail="You must make a deposit before withdrawing Spin earnings.")
        wallet.spin_balance = float(wallet.spin_balance) - amount
        source = "spin"
    else:
        raise HTTPException(status_code=400, detail="Insufficient withdrawable balance.")

    db.add(Transaction(
        user_id=current_user.id, amount=amount, transaction_type="WITHDRAW", status="PENDING",
        meta={"destination": body.destination.strip(), "source": source, "fee": fee, "net": round(amount - fee, 2)},
    ))
    db.commit()
    return {"message": f"Withdrawal request submitted. You will receive ${amount - fee:.2f} after the ${fee:.2f} fee, within about {rules['withdraw_processing_days']} day(s) after review.", "status": "PENDING", "fee": fee, "net": round(amount - fee, 2)}


@router.get("/airdrops", response_model=list[AirdropResponse])
def get_user_airdrops(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Airdrop).filter(Airdrop.is_active == True).order_by(Airdrop.created_at.desc()).all()


# ==========================================
# READ-ONLY CONFIG LISTS (used by the admin Widgets / Settings pages)
# ==========================================

@router.get("/dashboard-layout")
def get_dashboard_layout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    value = _setting(db, "DASHBOARD_LAYOUT", [])
    return value if isinstance(value, list) else []


@router.get("/custom-elements")
def get_custom_elements(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    value = _setting(db, "CUSTOM_ELEMENTS", [])
    return value if isinstance(value, list) else []


# ==========================================
# REFERRAL NETWORK (real numbers only)
# ==========================================

@router.get("/network")
def get_network(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Referral code, number of people who signed up with it, and commissions actually credited."""
    if not current_user.referral_code:
        for _ in range(5):
            code = secrets.token_urlsafe(6).replace("-", "a").replace("_", "b")[:8]
            if not db.query(User).filter(User.referral_code == code).first():
                current_user.referral_code = code
                db.commit()
                break
    team = db.query(User).filter(User.referred_by == current_user.id).count()
    earned = sum(float(t.amount) for t in db.query(Transaction).filter(
        Transaction.user_id == current_user.id, Transaction.transaction_type == "REFERRAL_COMMISSION",
        Transaction.status == "SUCCESS").all())
    return {"referral_code": current_user.referral_code, "level1_count": team, "commission_total": round(earned, 2)}

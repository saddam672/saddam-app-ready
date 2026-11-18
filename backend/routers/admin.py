from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import logging
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from limiter import client_ip
from models import (
    User, DashboardWidget, AppConfig, TradingSignal, SystemLog, Wallet, Airdrop,
    Transaction, ConsentLog, AuditLog,
)
from schemas import (
    DashboardWidgetUpdate, DashboardWidgetResponse, AppConfigUpdate, AppConfigResponse,
    UserResponse, SignalCreate, AirdropCreate, AirdropResponse, UserAdminDetail,
    BalanceUpdate, ReasonBody, PasswordResetBody, WithdrawReview, AuditLogResponse,
)
from auth import get_current_admin
from security import get_password_hash

logger = logging.getLogger(__name__)
router = APIRouter()


def audit(db: Session, admin: User, request: Request, action: str, target_type: str = None,
          target_id: str = None, before=None, after=None, reason: str = None):
    """Records WHO did WHAT, before/after values, why, and from which IP. Call before db.commit()."""
    db.add(AuditLog(
        admin_id=admin.id, admin_email=admin.email, action=action, target_type=target_type,
        target_id=str(target_id) if target_id else None, before_value=before, after_value=after,
        reason=reason, ip_address=client_ip(request),
    ))


def _get_user_or_404(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# 1. USER MANAGEMENT
@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(User).filter(User.role == "USER").order_by(User.created_at.desc()).limit(2000).all()

@router.get("/users/{user_id}", response_model=UserAdminDetail)
def get_user_detail(user_id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = _get_user_or_404(db, user_id)
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    data = UserResponse.model_validate(user).model_dump()
    data.update({
        "last_spin_at": user.last_spin_at,
        "real_balance": float(wallet.real_balance) if wallet else 0,
        "bonus_balance": float(wallet.bonus_balance) if wallet else 0,
        "spin_balance": float(wallet.spin_balance) if wallet else 0,
        "total_earned": float(wallet.total_earned) if wallet else 0,
    })
    return data

@router.get("/users/{user_id}/consents")
def get_user_consents(user_id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    rows = db.query(ConsentLog).filter(ConsentLog.user_id == user_id).order_by(ConsentLog.created_at.desc()).limit(50).all()
    return [{"id": str(r.id), "consent_type": r.consent_type, "action": r.action, "version": r.version,
             "ip_address": r.ip_address, "created_at": r.created_at} for r in rows]

@router.put("/users/{user_id}/update-balances")
def update_user_balances(user_id: str, body: BalanceUpdate, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    """Manual balance edit. A written reason is mandatory and the change is stored in the audit log."""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).with_for_update().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    before = {"real": float(wallet.real_balance), "bonus": float(wallet.bonus_balance), "spin": float(wallet.spin_balance)}
    wallet.real_balance, wallet.bonus_balance, wallet.spin_balance = body.real_balance, body.bonus_balance, body.spin_balance
    after = {"real": body.real_balance, "bonus": body.bonus_balance, "spin": body.spin_balance}
    audit(db, current_admin, request, "BALANCE_EDIT", "user", user_id, before, after, body.reason)
    db.commit()
    return {"message": "Balances updated", "before": before, "after": after}

@router.put("/users/{user_id}/freeze")
def toggle_freeze_user(user_id: str, body: ReasonBody, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = _get_user_or_404(db, user_id)
    if user.role == "ADMIN":
        raise HTTPException(status_code=400, detail="Cannot freeze an admin")
    before = {"is_frozen": user.is_frozen}
    user.is_frozen = not user.is_frozen
    user.is_active = not user.is_frozen
    if user.is_frozen:
        user.trading_consent = False
        user.auto_trade_active = False
    audit(db, current_admin, request, "USER_FREEZE" if user.is_frozen else "USER_UNFREEZE", "user", user_id, before, {"is_frozen": user.is_frozen}, body.reason)
    db.commit()
    return {"message": "Updated", "is_frozen": user.is_frozen}

@router.put("/users/{user_id}/reset-password")
def admin_reset_password(user_id: str, body: PasswordResetBody, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = _get_user_or_404(db, user_id)
    user.password_hash = get_password_hash(body.new_password)
    audit(db, current_admin, request, "PASSWORD_RESET", "user", user_id, None, None, body.reason)
    db.commit()
    return {"message": "Reset successful"}

@router.get("/users/{user_id}/transactions")
def get_user_transactions(user_id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(20).all()

@router.put("/transactions/{tx_id}/refund")
def refund_transaction(tx_id: str, body: ReasonBody, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx or tx.status != "SUCCESS":
        raise HTTPException(status_code=400, detail="Cannot refund")
    wallet = db.query(Wallet).filter(Wallet.user_id == tx.user_id).with_for_update().first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    before = {"real": float(wallet.real_balance)}
    if tx.transaction_type in ["DEPOSIT", "WALLET_TOPUP"]:
        if float(wallet.real_balance) < float(tx.amount):
            raise HTTPException(status_code=400, detail="User balance is lower than the amount to refund")
        wallet.real_balance = float(wallet.real_balance) - float(tx.amount)
    elif tx.transaction_type == "WITHDRAW":
        wallet.real_balance = float(wallet.real_balance) + float(tx.amount)
    else:
        raise HTTPException(status_code=400, detail="This transaction type cannot be refunded here")
    tx.status = "REFUNDED"
    audit(db, current_admin, request, "TX_REFUND", "transaction", tx_id, before, {"real": float(wallet.real_balance)}, body.reason)
    db.commit()
    return {"message": "Refunded"}

# WITHDRAWAL REVIEW
@router.get("/withdrawals")
def list_withdrawals(status: str = "PENDING", db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    rows = (db.query(Transaction, User).join(User, User.id == Transaction.user_id)
            .filter(Transaction.transaction_type == "WITHDRAW", Transaction.status == status.upper())
            .order_by(Transaction.created_at.asc()).limit(200).all())
    return [{"id": str(t.id), "user_id": str(u.id), "email": u.email, "full_name": u.full_name,
             "amount": float(t.amount), "status": t.status, "destination": (t.meta or {}).get("destination"),
             "source": (t.meta or {}).get("source"), "fee": (t.meta or {}).get("fee", 0), "net": (t.meta or {}).get("net", float(t.amount)), "txid": t.payment_gateway_id, "note": t.note,
             "created_at": t.created_at} for t, u in rows]

@router.put("/withdrawals/{tx_id}/review")
def review_withdrawal(tx_id: str, body: WithdrawReview, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    """Approve = payout was sent (enter the TXID in note). Reject = held amount goes back to the user."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.transaction_type == "WITHDRAW").with_for_update().first()
    if not tx or tx.status != "PENDING":
        raise HTTPException(status_code=400, detail="Withdrawal not found or already reviewed")
    if body.approve and not (body.note and len(body.note.strip()) >= 6):
        raise HTTPException(status_code=400, detail="Enter the payout TXID / reference when approving")
    if not body.approve and not (body.note and body.note.strip()):
        raise HTTPException(status_code=400, detail="Enter a rejection reason")

    tx.reviewed_by, tx.reviewed_at = current_admin.id, datetime.now(timezone.utc)
    if body.approve:
        tx.status, tx.payment_gateway_id = "SUCCESS", body.note.strip()[:100]
    else:
        wallet = db.query(Wallet).filter(Wallet.user_id == tx.user_id).with_for_update().first()
        col = "spin_balance" if (tx.meta or {}).get("source") == "spin" else "real_balance"
        setattr(wallet, col, float(getattr(wallet, col)) + float(tx.amount))
        tx.status, tx.note = "REJECTED", body.note.strip()[:255]
    audit(db, current_admin, request, "WITHDRAW_APPROVE" if body.approve else "WITHDRAW_REJECT", "transaction", tx_id,
          {"status": "PENDING", "amount": float(tx.amount)}, {"status": tx.status}, body.note)
    db.commit()
    return {"message": "Withdrawal " + ("approved" if body.approve else "rejected"), "status": tx.status}

# AUDIT LOG
@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(limit: int = 200, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()

# 2. AIRDROP
@router.post("/airdrops", response_model=AirdropResponse)
def create_airdrop(data: AirdropCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    a = Airdrop(**data.model_dump()); db.add(a); db.commit(); db.refresh(a); return a

@router.get("/airdrops", response_model=list[AirdropResponse])
def get_all_airdrops(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(Airdrop).order_by(Airdrop.created_at.desc()).all()

@router.delete("/airdrops/{id}")
def delete_airdrop(id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    a = db.query(Airdrop).filter(Airdrop.id == id).first()
    if a: db.delete(a); db.commit()
    return {"message": "Deleted"}

# 4. LAYOUT & WIDGETS
@router.get("/widgets", response_model=List[DashboardWidgetResponse])
def get_all_widgets(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(DashboardWidget).order_by(DashboardWidget.display_order.asc()).all()

@router.put("/widgets/{widget_name}", response_model=DashboardWidgetResponse)
def update_widget_status(widget_name: str, widget_data: DashboardWidgetUpdate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    w = db.query(DashboardWidget).filter(DashboardWidget.widget_name == widget_name).first()
    if not w: raise HTTPException(status_code=404, detail="Widget not found")
    w.is_active = widget_data.is_active
    if widget_data.display_order is not None: w.display_order = widget_data.display_order
    db.commit(); db.refresh(w); return w

class LayoutUpdate(BaseModel):
    layout: List[dict]

@router.put("/dashboard-layout")
def update_dashboard_layout(data: LayoutUpdate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    c = db.query(AppConfig).filter(AppConfig.config_key == "DASHBOARD_LAYOUT").first()
    if c: c.config_value = data.layout
    else: db.add(AppConfig(config_key="DASHBOARD_LAYOUT", config_value=data.layout))
    db.commit(); return {"message": "Layout updated"}

# 5. CONFIG & SIGNALS
@router.get("/config")
def list_app_config(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return {c.config_key: c.config_value for c in db.query(AppConfig).all()}

@router.get("/subscriptions")
def list_all_subscriptions(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    from models import UserSubscription, SubscriptionPlan
    rows = (db.query(UserSubscription, User, SubscriptionPlan)
            .join(User, User.id == UserSubscription.user_id)
            .outerjoin(SubscriptionPlan, SubscriptionPlan.id == UserSubscription.plan_id)
            .order_by(UserSubscription.start_date.desc()).limit(500).all())
    now = datetime.now(timezone.utc)
    out = []
    for sub, u, plan in rows:
        end = sub.end_date
        if end is not None and end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)
        out.append({"id": str(sub.id), "user_name": u.full_name, "user_email": u.email,
                    "plan_name": plan.plan_name if plan else "Unknown",
                    "is_active": bool(sub.is_active and (end is None or end > now)),
                    "start_date": sub.start_date, "end_date": sub.end_date,
                    "amount_paid": float(plan.price) if plan else 0})
    return out

@router.put("/config", response_model=AppConfigResponse)
def update_app_config(config_data: AppConfigUpdate, request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    c = db.query(AppConfig).filter(AppConfig.config_key == config_data.config_key).first()
    before = c.config_value if c else None
    if c: c.config_value = config_data.config_value
    else:
        c = AppConfig(config_key=config_data.config_key, config_value=config_data.config_value, description=config_data.description); db.add(c)
    audit(db, current_admin, request, "CONFIG_UPDATE", "config", config_data.config_key, before, config_data.config_value)
    db.commit(); db.refresh(c); return c

@router.put("/spin-prizes")
def update_spin_prizes(prizes: List[float], request: Request, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if not prizes or any(p < 0 for p in prizes):
        raise HTTPException(status_code=400, detail="Prizes must be a non-empty list of non-negative numbers")
    c = db.query(AppConfig).filter(AppConfig.config_key == "SPIN_PRIZES").first()
    before = c.config_value if c else None
    if c: c.config_value = prizes
    else: db.add(AppConfig(config_key="SPIN_PRIZES", config_value=prizes))
    audit(db, current_admin, request, "SPIN_PRIZES_UPDATE", "config", "SPIN_PRIZES", before, prizes)
    db.commit(); return {"message": "Updated"}

@router.post("/signals", status_code=201)
def create_signal(signal_data: SignalCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    s = TradingSignal(pair=signal_data.pair, signal_type=signal_data.signal_type, entry_price=signal_data.entry_price, target_price=signal_data.target_price, stop_loss=signal_data.stop_loss, status="ACTIVE")
    db.add(s); db.commit(); db.refresh(s); return s

@router.delete("/signals/{signal_id}", status_code=204)
def delete_signal(signal_id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    s = db.query(TradingSignal).filter(TradingSignal.id == signal_id).first()
    if s: db.delete(s); db.commit()
    return None

@router.get("/diagnostics")
def get_system_logs(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin), limit: int = 100):
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    return [{"id": str(l.id), "user_id": str(l.user_id) if l.user_id else None, "error_type": l.error_type, "error_message": l.error_message, "is_resolved": l.is_resolved, "created_at": l.created_at} for l in logs]

@router.put("/diagnostics/{log_id}/resolve")
def resolve_log(log_id: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    l = db.query(SystemLog).filter(SystemLog.id == log_id).first()
    if l: l.is_resolved = True; db.commit()
    return {"message": "Resolved"}

@router.get("/binance-symbols")
def get_binance_symbols(current_admin: User = Depends(get_current_admin)):
    import requests as req_lib
    try:
        resp = req_lib.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=15)
        data = resp.json(); symbols = []
        for item in data:
            sym = item.get("symbol", "")
            if not sym.endswith("USDT") or any(x in sym for x in ["UP", "DOWN", "BEAR", "BULL", "USDC", "BUSD", "DAI", "TUSD"]): continue
            try: symbols.append({"symbol": sym, "type": "FUTURES", "volume": float(item.get("quoteVolume", 0))})
            except: pass
        symbols.sort(key=lambda x: x["symbol"])
        return {"count": len(symbols), "symbols": symbols}
    except: return {"count": 0, "symbols": []}

class GeneratorConfig(BaseModel):
    timeframe: str = "1h"
    max_coins: int = 500

@router.post("/run-signal-generator")
def start_signal_generator(config: GeneratorConfig, current_admin: User = Depends(get_current_admin)):
    import threading
    from services.generator_jobs import create_job, cleanup_old_jobs
    from services.signal_generator_wrapper import run_signal_generator
    from database import SessionLocal
    cleanup_old_jobs(); job_id = create_job()
    def bg_task():
        db = SessionLocal()
        try: run_signal_generator(db=db, max_pairs=config.max_coins, interval=config.timeframe, min_volume_usdt=1000000, use_mtf=True, max_workers=10, job_id=job_id)
        finally: db.close()
    threading.Thread(target=bg_task, daemon=True).start()
    return {"job_id": job_id, "status": "started"}

@router.get("/generator-status/{job_id}")
def get_generator_status(job_id: str, current_admin: User = Depends(get_current_admin)):
    from services.generator_jobs import get_job
    job = get_job(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/analyze-signals")
def analyze_signals(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    from services.signal_analyzer import analyze_all_signals
    try: return analyze_all_signals(db)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
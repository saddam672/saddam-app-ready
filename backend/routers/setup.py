"""
Site profile / first-run setup.

Everything here has a SAFE DEFAULT, so the app is fully usable even if the owner
never opens the setup page. The owner can fill it in (or change it) any time from /setup.

  GET  /api/v1/setup/profile   public  -> profile used by legal pages, footer, wallet rules
  GET  /api/v1/setup/status    admin   -> is setup completed / skipped
  PUT  /api/v1/setup/profile   admin   -> save profile (audited)
  POST /api/v1/setup/skip      admin   -> "use defaults", stop showing the wizard
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_admin
from database import get_db
from models import AppConfig, User

router = APIRouter()

PROFILE_KEY = "SITE_PROFILE"
SETUP_KEY = "SETUP_STATE"

# Used whenever a field is empty. Chosen so nothing looks broken and nothing is made up
# (no invented company, address or licence).
DEFAULT_PROFILE = {
    "company_name": "TradeMaster",
    "legal_entity": "",            # e.g. "TradeMaster Ltd."  (blank -> company_name is used)
    "country": "",
    "address": "",
    "support_email": "support@example.com",
    "support_hours": "24/7 via in-app chat",
    "governing_law": "",           # blank -> country is used, or a neutral sentence
    "min_age": 18,
    "restricted_countries": "",    # free text list, shown in Terms
    # money rules (these are ENFORCED by the backend, not just displayed)
    "min_deposit": 1.0,
    "min_withdrawal": 10.0,
    "max_withdrawal": 0.0,         # 0 = no maximum
    "withdraw_fee_percent": 1.5,
    "withdraw_fee_flat": 0.0,
    "withdraw_processing_days": 3,
    "daily_withdraw_limit": 0.0,   # 0 = no daily limit (per user)
    "refund_policy": "Subscription payments are non-refundable once access has been used, unless required by law. Contact support within 7 days if you were charged by mistake.",
    "bonus_conditions": "Spin and bonus balances can be withdrawn only after the account has made at least one deposit.",
}

DEFAULT_STATE = {"completed": False, "skipped": False}

NUMERIC = {
    "min_age": (13, 99), "min_deposit": (0, 1_000_000), "min_withdrawal": (0, 1_000_000),
    "max_withdrawal": (0, 100_000_000), "withdraw_fee_percent": (0, 50), "withdraw_fee_flat": (0, 100_000),
    "withdraw_processing_days": (0, 60), "daily_withdraw_limit": (0, 100_000_000),
}
TEXT_MAX = {"company_name": 80, "legal_entity": 120, "country": 80, "address": 250, "support_email": 120,
            "support_hours": 120, "governing_law": 120, "restricted_countries": 400,
            "refund_policy": 1200, "bonus_conditions": 1200}


def _get(db: Session, key: str, default):
    row = db.query(AppConfig).filter(AppConfig.config_key == key).first()
    return row.config_value if row else default


def _put(db: Session, key: str, value, desc: str):
    row = db.query(AppConfig).filter(AppConfig.config_key == key).first()
    if row:
        row.config_value = value
    else:
        db.add(AppConfig(config_key=key, config_value=value, description=desc))


def get_profile(db: Session) -> dict:
    """Saved profile merged over defaults; empty values fall back to the default."""
    saved = _get(db, PROFILE_KEY, {}) or {}
    merged = dict(DEFAULT_PROFILE)
    for k, v in saved.items():
        if k in DEFAULT_PROFILE and v not in (None, ""):
            merged[k] = v
    return merged


class ProfileBody(BaseModel):
    company_name: Optional[str] = None
    legal_entity: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    support_email: Optional[str] = None
    support_hours: Optional[str] = None
    governing_law: Optional[str] = None
    restricted_countries: Optional[str] = None
    refund_policy: Optional[str] = None
    bonus_conditions: Optional[str] = None
    min_age: Optional[float] = None
    min_deposit: Optional[float] = None
    min_withdrawal: Optional[float] = None
    max_withdrawal: Optional[float] = None
    withdraw_fee_percent: Optional[float] = None
    withdraw_fee_flat: Optional[float] = None
    withdraw_processing_days: Optional[float] = None
    daily_withdraw_limit: Optional[float] = None
    complete: bool = Field(default=True, description="mark setup as completed")


@router.get("/profile")
def public_profile(db: Session = Depends(get_db)):
    p = get_profile(db)
    return {"profile": p, "terms_entity": p["legal_entity"] or p["company_name"]}


@router.get("/status")
def setup_status(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    state = {**DEFAULT_STATE, **(_get(db, SETUP_KEY, {}) or {})}
    saved = _get(db, PROFILE_KEY, {}) or {}
    return {**state, "profile": get_profile(db), "defaults": DEFAULT_PROFILE,
            "filled_fields": [k for k, v in saved.items() if v not in (None, "")]}


@router.put("/profile")
def save_profile(body: ProfileBody, request: Request, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    data = body.model_dump(exclude_unset=True)
    complete = data.pop("complete", True)
    clean = dict(_get(db, PROFILE_KEY, {}) or {})

    for k, v in data.items():
        if k in NUMERIC:
            if v is None:
                clean.pop(k, None)
                continue
            lo, hi = NUMERIC[k]
            if not (lo <= v <= hi):
                raise HTTPException(status_code=400, detail=f"{k} must be between {lo} and {hi}")
            clean[k] = int(v) if k in ("min_age", "withdraw_processing_days") else round(float(v), 2)
        elif k in TEXT_MAX:
            v = (v or "").strip()
            if len(v) > TEXT_MAX[k]:
                raise HTTPException(status_code=400, detail=f"{k} is too long (max {TEXT_MAX[k]})")
            if k == "support_email" and v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
                raise HTTPException(status_code=400, detail="Support email is not valid")
            clean[k] = v

    max_w, min_w = clean.get("max_withdrawal", 0) or 0, clean.get("min_withdrawal", DEFAULT_PROFILE["min_withdrawal"])
    if max_w and max_w < min_w:
        raise HTTPException(status_code=400, detail="Maximum withdrawal cannot be smaller than the minimum")

    _put(db, PROFILE_KEY, clean, "Company / contact / fee profile (setup page)")

    # keep the older APP_SETTINGS keys in sync so existing screens keep working
    app_settings = dict(_get(db, "APP_SETTINGS", {}) or {})
    merged = get_profile_from(clean)
    app_settings.update({"support_email": merged["support_email"], "min_withdrawal": merged["min_withdrawal"],
                         "min_deposit": merged["min_deposit"]})
    _put(db, "APP_SETTINGS", app_settings, "Global app settings")

    state = {"completed": bool(complete), "skipped": False}
    _put(db, SETUP_KEY, state, "First-run setup state")
    try:
        from routers.admin import audit
        audit(db, admin, request, "SETUP_SAVE", "site_profile", "profile", None, clean, "Setup page")
    except Exception:
        pass
    db.commit()
    return {"message": "Saved", "profile": get_profile(db), **state}


def get_profile_from(saved: dict) -> dict:
    merged = dict(DEFAULT_PROFILE)
    merged.update({k: v for k, v in saved.items() if k in DEFAULT_PROFILE and v not in (None, "")})
    return merged


@router.post("/skip")
def skip_setup(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    _put(db, SETUP_KEY, {"completed": False, "skipped": True}, "First-run setup state")
    db.commit()
    return {"message": "Using default settings. You can open /setup any time to fill them in.", "skipped": True}

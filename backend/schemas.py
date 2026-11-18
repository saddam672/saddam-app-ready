from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from models import UserRole

class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    accepted_terms: bool = Field(..., description="Must be true: Terms, Privacy Policy and Risk Disclosure accepted")
    terms_version: Optional[str] = None
    ref: Optional[str] = Field(None, max_length=20, description="Referral code of the person who invited you")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_verified: bool
    onboarding_step: int
    is_active: bool
    has_deposited: bool
    created_at: datetime
    avatar_url: Optional[str] = None
    is_frozen: bool = False
    is_vip: bool = False
    terms_version: Optional[str] = None
    trading_consent: bool = False
    trading_consent_at: Optional[datetime] = None
    show_in_feed: bool = False
    model_config = ConfigDict(from_attributes=True)

class UserAdminDetail(UserResponse):
    real_balance: float
    spin_balance: float
    bonus_balance: float
    total_earned: float
    last_spin_at: Optional[datetime] = None

class UserApiKeyCreate(BaseModel):
    api_key: str = Field(..., min_length=10)
    secret_key: str = Field(..., min_length=10)

class UserApiKeyResponse(BaseModel):
    id: UUID
    exchange_name: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class WalletResponse(BaseModel):
    real_balance: float
    bonus_balance: float
    spin_balance: float
    total_earned: float
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    transaction_type: str = Field(..., description="DEPOSIT, WITHDRAW, SUBSCRIBE")

class TransactionResponse(BaseModel):
    id: UUID
    amount: float
    transaction_type: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SubscriptionPlanResponse(BaseModel):
    id: UUID
    plan_name: str
    price: float
    duration_days: int
    features: Optional[Dict[str, Any]] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class SignalCreate(BaseModel):
    pair: str = Field(..., min_length=2, max_length=20)
    signal_type: str = Field(..., description="BUY or SELL")
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

class SignalResponse(BaseModel):
    id: UUID
    pair: str
    signal_type: str
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    status: str
    created_at: datetime
    effectiveness_score: Optional[int] = None
    effectiveness_reason: Optional[str] = None
    candle_pattern: Optional[str] = None
    chart_pattern: Optional[str] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    entry_zone: Optional[str] = None
    analysis_details: Optional[str] = None
    current_price: Optional[float] = None
    trailing_sl: Optional[float] = None
    position_size: Optional[float] = None
    regime: Optional[str] = None
    rsi: Optional[float] = None
    reason: Optional[str] = None
    sl_percent: Optional[float] = None
    tp_percent: Optional[float] = None
    votes_buy: Optional[int] = None
    votes_sell: Optional[int] = None
    votes_hold: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class DashboardWidgetUpdate(BaseModel):
    is_active: bool
    display_order: Optional[int] = None
    target_audience: Optional[str] = "ALL"

class DashboardWidgetResponse(BaseModel):
    widget_name: str
    is_active: bool
    display_order: int
    target_audience: str
    model_config = ConfigDict(from_attributes=True)

class AppConfigUpdate(BaseModel):
    config_key: str
    config_value: Dict[str, Any]
    description: Optional[str] = None

class AppConfigResponse(BaseModel):
    config_key: str
    config_value: Dict[str, Any]
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AirdropCreate(BaseModel):
    title: str
    description: Optional[str] = None
    link_url: str
    video_url: Optional[str] = None

class AirdropResponse(AirdropCreate):
    id: UUID
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SpinConfig(BaseModel):
    prizes: List[float]

class SpinResponse(BaseModel):
    success: bool
    reward_amount: float
    prize_index: int = 0
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str
    verification_required: bool = False

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None

# ==========================================
# CONSENT, WITHDRAWALS, AUDIT
# ==========================================
class TradingConsentRequest(BaseModel):
    accepted: bool
    version: str

class ConsentStatus(BaseModel):
    current_terms_version: str
    accepted_terms_version: Optional[str] = None
    terms_up_to_date: bool
    trading_consent: bool
    trading_consent_at: Optional[datetime] = None
    can_trade: bool

class BalanceUpdate(BaseModel):
    real_balance: float = Field(..., ge=0)
    bonus_balance: float = Field(..., ge=0)
    spin_balance: float = Field(..., ge=0)
    reason: str = Field(..., min_length=5, max_length=500)

class ReasonBody(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)

class PasswordResetBody(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=100)
    reason: str = Field(..., min_length=3, max_length=500)

class WithdrawRequestBody(BaseModel):
    amount: float = Field(..., gt=0)
    destination: str = Field(..., min_length=10, max_length=200, description="Wallet address / account to receive the payout")

class WithdrawReview(BaseModel):
    approve: bool
    note: Optional[str] = Field(None, max_length=255, description="TXID if approved, or rejection reason")

class AuditLogResponse(BaseModel):
    id: UUID
    admin_email: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    before_value: Optional[Any] = None
    after_value: Optional[Any] = None
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

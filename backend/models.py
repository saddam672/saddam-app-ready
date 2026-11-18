import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum, Text
from sqlalchemy import JSON as JSONB
from sqlalchemy.types import TypeDecorator, CHAR

class UUID(TypeDecorator):
    """Platform-independent UUID type (works on SQLite, MySQL, and PostgreSQL)."""
    impl = CHAR(36)
    cache_ok = True

    def __init__(self, as_uuid=True):
        super().__init__()
        self.as_uuid = as_uuid

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value

from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    is_verified = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(255), nullable=True)
    has_deposited = Column(Boolean, default=False)
    last_spin_at = Column(DateTime(timezone=True), nullable=True)
    
    # নতুন ফিল্ড
    is_vip = Column(Boolean, default=False)
    auto_trade_active = Column(Boolean, default=False)
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    is_frozen = Column(Boolean, default=False)

    # Legal consent (Terms / Privacy / Risk) and trading permission
    accepted_terms_at = Column(DateTime(timezone=True), nullable=True)
    terms_version = Column(String(20), nullable=True)
    trading_consent = Column(Boolean, default=False, nullable=False)
    trading_consent_at = Column(DateTime(timezone=True), nullable=True)
    trading_consent_version = Column(String(20), nullable=True)
    # Opt-in: user agrees to appear (masked name) in the public activity feed / leaderboard
    show_in_feed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", foreign_keys="Transaction.user_id")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan")

class UserApiKey(Base):
    __tablename__ = 'user_api_keys'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    exchange_name = Column(String(50), default='BINANCE')
    api_key_encrypted = Column(Text, nullable=False)
    secret_key_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="api_keys")

class Wallet(Base):
    __tablename__ = 'wallets'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    real_balance = Column(Numeric(15, 2), default=0.00)
    bonus_balance = Column(Numeric(15, 2), default=0.00)
    spin_balance = Column(Numeric(15, 2), default=0.00)
    total_earned = Column(Numeric(15, 2), default=0.00)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="wallet")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    status = Column(String(20), default='PENDING')
    payment_gateway_id = Column(String(100), nullable=True)
    note = Column(String(255), nullable=True)
    meta = Column(JSONB, nullable=True)   # e.g. {"destination": "...", "source": "real", "txid": "..."}
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_name = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    features = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)

class UserSubscription(Base):
    __tablename__ = 'user_subscriptions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('subscription_plans.id'))
    start_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")

class TradingSignal(Base):
    __tablename__ = 'trading_signals'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    entry_price = Column(Numeric(15, 4), nullable=True)
    target_price = Column(Numeric(15, 4), nullable=True)
    stop_loss = Column(Numeric(15, 4), nullable=True)
    status = Column(String(20), default='ACTIVE')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    effectiveness_score = Column(Integer, nullable=True)
    effectiveness_reason = Column(Text, nullable=True)
    candle_pattern = Column(String(100), nullable=True)
    chart_pattern = Column(String(100), nullable=True)
    support_level = Column(Numeric(15, 4), nullable=True)
    resistance_level = Column(Numeric(15, 4), nullable=True)
    entry_zone = Column(String(200), nullable=True)
    analysis_details = Column(Text, nullable=True)
    current_price = Column(Numeric(15, 4), nullable=True)
    trailing_sl = Column(Numeric(15, 4), nullable=True)
    position_size = Column(Numeric(10, 4), nullable=True)
    regime = Column(String(50), nullable=True)
    rsi = Column(Numeric(10, 2), nullable=True)
    reason = Column(String(255), nullable=True)
    sl_percent = Column(Numeric(10, 2), nullable=True)
    tp_percent = Column(Numeric(10, 2), nullable=True)
    votes_buy = Column(Integer, nullable=True)
    votes_sell = Column(Integer, nullable=True)
    votes_hold = Column(Integer, nullable=True)

class AppConfig(Base):
    __tablename__ = 'app_configs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DashboardWidget(Base):
    __tablename__ = 'dashboard_widgets'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    widget_name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=1)
    target_audience = Column(String(50), default='ALL')
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    subject = Column(String(255), nullable=True)
    status = Column(String(20), default='OPEN')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="support_tickets")

class SystemLog(Base):
    __tablename__ = 'system_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Airdrop(Base):
    __tablename__ = 'airdrops'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    link_url = Column(String(500), nullable=False)
    video_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Banner(Base):
    __tablename__ = 'banners'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_url = Column(String(500), nullable=False)
    link_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ConsentLog(Base):
    """Immutable record of every time a user accepts / revokes legal terms or trading permission."""
    __tablename__ = 'consent_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    consent_type = Column(String(30), nullable=False)   # TERMS | TRADING
    action = Column(String(10), nullable=False)         # ACCEPT | REVOKE
    version = Column(String(20), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Every sensitive admin action: who, what, before/after, reason, IP."""
    __tablename__ = 'audit_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    admin_email = Column(String(150), nullable=True)
    action = Column(String(60), nullable=False, index=True)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(64), nullable=True)
    before_value = Column(JSONB, nullable=True)
    after_value = Column(JSONB, nullable=True)
    reason = Column(String(500), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

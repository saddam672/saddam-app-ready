"""
Run ONCE after the first start to create the initial data.

    python seed_data.py

Creates:
    - 1 admin user  (email/password from ADMIN_EMAIL / ADMIN_PASSWORD in .env;
                     if ADMIN_PASSWORD is empty a strong random one is generated and printed ONCE)
    - default dashboard widgets
    - default app configs (maintenance, limits, spin prizes, announcements)
    - 4 subscription plans

It does NOT create any fake users, fake earnings or fake signals.
Safe to re-run: existing data is not duplicated.
"""
import os
import secrets
import string
from datetime import datetime, timezone

from database import SessionLocal, engine
from legal import TERMS_VERSION
from models import Base, User, UserRole, Wallet, DashboardWidget, AppConfig, SubscriptionPlan
from security import get_password_hash

WEAK_PASSWORDS = {"admin@12345", "admin123", "password", "12345678", "changeme"}


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Seeding database...")
        print("=" * 60)

        # ---------------- 1. ADMIN ----------------
        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        if not admin_email:
            raise SystemExit("Set ADMIN_EMAIL in your .env file before running the seed.")

        admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
        generated = False
        if not admin_password:
            admin_password, generated = _random_password(), True
        elif len(admin_password) < 12 or admin_password.lower() in WEAK_PASSWORDS:
            raise SystemExit("ADMIN_PASSWORD is too weak. Use at least 12 characters, or leave it empty to auto-generate one.")

        if not db.query(User).filter(User.email == admin_email).first():
            admin = User(
                full_name="Super Admin",
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                is_verified=True,
                is_active=True,
                accepted_terms_at=datetime.now(timezone.utc),
                terms_version=TERMS_VERSION,
            )
            db.add(admin)
            db.flush()
            db.add(Wallet(user_id=admin.id))
            db.commit()
            print(f"Admin created: {admin_email}")
            if generated:
                print(f"   Generated password (shown ONLY ONCE, save it now): {admin_password}")
                # cPanel has no visible console, so also keep it in a file next to the app.
                # Log in, change the password in Profile, then DELETE this file.
                try:
                    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FIRST_ADMIN_LOGIN.txt")
                    with open(path, "w") as f:
                        f.write(f"Admin email:    {admin_email}\nAdmin password: {admin_password}\n\nLog in, change the password in Profile, then DELETE this file.\n")
                    os.chmod(path, 0o600)
                except Exception:
                    pass
        else:
            print(f"Admin already exists ({admin_email})")

        # ---------------- 2. WIDGETS ----------------
        widgets = [
            ("live_ticker", 1, "ALL"), ("live_prices", 2, "ALL"), ("wallet", 3, "ALL"),
            ("signals", 4, "ALL"), ("binance_balance", 5, "ALL"), ("auto_copy", 6, "ALL"),
            ("leaderboard", 7, "PREMIUM"), ("news_board", 8, "ALL"),
            ("spin_wheel", 9, "ALL"), ("airdrops", 10, "ALL"),
        ]
        new = 0
        for name, order, audience in widgets:
            if not db.query(DashboardWidget).filter(DashboardWidget.widget_name == name).first():
                db.add(DashboardWidget(widget_name=name, is_active=True, display_order=order, target_audience=audience))
                new += 1
        db.commit()
        print(f"Widgets: {new} created")

        # ---------------- 3. CONFIGS ----------------
        configs = [
            ("MAINTENANCE_MODE", {"status": False}, "When true, users see the maintenance screen"),
            ("APP_SETTINGS", {"app_version": "1.0.0", "support_email": os.getenv("SUPPORT_EMAIL", "support@example.com"),
                              "min_withdrawal": 10.0, "min_deposit": 1.0}, "Global app settings"),
            ("SPIN_PRIZES", [0.001, 0.002, 0.005, 0.008, 0.01, 0.0, 0.003, 0.004], "Daily spin prizes (all equally likely)"),
            ("ANNOUNCEMENTS", {"items": []}, "News/announcements shown on the user dashboard"),
        ]
        new = 0
        for key, value, desc in configs:
            if not db.query(AppConfig).filter(AppConfig.config_key == key).first():
                db.add(AppConfig(config_key=key, config_value=value, description=desc))
                new += 1
        db.commit()
        print(f"App configs: {new} created")

        # ---------------- 4. PLANS ----------------
        plans = [
            ("1 Month", 29.99, 30, {"signals": True, "auto_copy": True, "priority_support": False}),
            ("6 Months", 149.99, 180, {"signals": True, "auto_copy": True, "priority_support": True}),
            ("1 Year", 249.99, 365, {"signals": True, "auto_copy": True, "priority_support": True, "bonus": "20% off"}),
            ("Lifetime", 599.99, 99999, {"signals": True, "auto_copy": True, "priority_support": True, "vip_group": True}),
        ]
        new = 0
        for name, price, days, features in plans:
            if not db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == name).first():
                db.add(SubscriptionPlan(plan_name=name, price=price, duration_days=days, features=features, is_active=True))
                new += 1
        db.commit()
        print(f"Subscription plans: {new} created")

        print("=" * 60)
        print("Done. Log in at /login with the admin email and change the password in Profile.")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

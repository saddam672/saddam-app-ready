"""
Background scheduled tasks for the trading app.

Usage:
    # Run all jobs once:
    python -m services.cron_jobs all

    # Run specific job:
    python -m services.cron_jobs expire
    python -m services.cron_jobs reminders

Production recommendation:
    - Use Linux cron: */5 * * * * cd /path/to/backend && python -m services.cron_jobs all
    - Or use APScheduler / Celery Beat for advanced scheduling.
"""
from database import SessionLocal
from models import UserSubscription, AppConfig, User
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


def expire_old_subscriptions():
    """Mark expired subscriptions as inactive."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        expired = db.query(UserSubscription).filter(
            UserSubscription.is_active == True,
            UserSubscription.end_date < now
        ).all()

        for sub in expired:
            sub.is_active = False

        db.commit()
        logger.info(f"✅ Expired {len(expired)} subscriptions")
        return len(expired)
    except Exception as e:
        logger.error(f"❌ Failed to expire subscriptions: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def send_renewal_reminders():
    """
    Find subscriptions expiring in next 7 days.
    In production: send push notification / email here.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        week_later = now + timedelta(days=7)

        upcoming = db.query(UserSubscription).filter(
            UserSubscription.is_active == True,
            UserSubscription.end_date.between(now, week_later)
        ).all()

        # TODO: In production, iterate and send notifications here.
        for sub in upcoming:
            user = db.query(User).filter(User.id == sub.user_id).first()
            if user:
                logger.info(
                    f"📧 Renewal reminder needed: {user.email} "
                    f"(expires {sub.end_date.date()})"
                )

        logger.info(f"✅ Found {len(upcoming)} subscriptions expiring soon")
        return len(upcoming)
    except Exception as e:
        logger.error(f"❌ Failed to send renewal reminders: {e}")
        return 0
    finally:
        db.close()


def run_all_jobs():
    """Run all scheduled jobs in sequence."""
    logger.info("=" * 50)
    logger.info("🔄 Starting cron jobs batch...")
    logger.info("=" * 50)

    expired = expire_old_subscriptions()
    reminders = send_renewal_reminders()

    logger.info("=" * 50)
    logger.info("📊 Summary:")
    logger.info(f"   Expired subscriptions: {expired}")
    logger.info(f"   Renewal reminders:     {reminders}")
    logger.info("=" * 50)


# ==========================================
# CLI ENTRY POINT
# ==========================================
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    job = sys.argv[1] if len(sys.argv) > 1 else "all"

    if job == "all":
        run_all_jobs()
    elif job == "expire":
        expire_old_subscriptions()
    elif job == "reminders":
        send_renewal_reminders()
    else:
        print(f"Unknown job: {job}")
        print("Usage: python -m services.cron_jobs [all|expire|reminders]")
        sys.exit(1)
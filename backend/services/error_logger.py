from sqlalchemy.orm import Session
from models import SystemLog
import logging
import traceback

logger = logging.getLogger(__name__)


def log_error(
    db: Session,
    error_type: str,
    error_message: str,
    user_id: str = None,
    device_info: str = None,
    include_traceback: bool = False
):
    """
    Save system error to database for admin diagnostics.
    
    Args:
        db: SQLAlchemy database session
        error_type: Category of error (e.g., "API", "Payment", "Trade", "Frontend")
        error_message: The actual error message
        user_id: (Optional) The user ID who experienced the error
        device_info: (Optional) Browser/device information
        include_traceback: If True, appends Python stack trace (for debugging)
    """
    try:
        # If traceback requested, add it to the message
        if include_traceback:
            full_message = f"{error_message}\n\nTraceback:\n{traceback.format_exc()}"
        else:
            full_message = error_message
        
        log = SystemLog(
            user_id=user_id,
            error_type=error_type,
            error_message=full_message[:2000],  # Truncate to prevent DB overflow
            device_info=device_info,
            is_resolved=False
        )
        db.add(log)
        db.commit()
        logger.info(f"Error logged: {error_type} - {error_message[:100]}")
    except Exception as e:
        # If logging fails, don't crash the app — just print to console
        logger.error(f"Failed to save error log to DB: {e}")
        db.rollback()
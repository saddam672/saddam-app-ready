from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from legal import TERMS_VERSION
from models import AppConfig, DashboardWidget

router = APIRouter()

# ==========================================
# 1. GET APP INITIALIZATION CONFIG (Public)
# ==========================================

@router.get("/init", response_model=Dict[str, Any])
def get_app_initialization_config(db: Session = Depends(get_db)):
    """
    This API is called ONCE when the frontend app loads.
    It provides all dynamic settings, feature flags, and widget layouts
    so the frontend can render the UI accordingly without hardcoding.
    """
    
    # 1. Fetch all active widgets ordered by their display position
    active_widgets = db.query(DashboardWidget).filter(
        DashboardWidget.is_active == True
    ).order_by(DashboardWidget.display_order.asc()).all()
    
    widget_list = [
        {
            "name": w.widget_name,
            "order": w.display_order,
            "audience": w.target_audience
        } for w in active_widgets
    ]

    # 2. Fetch all global settings (Maintenance mode, limits, etc.)
    configs = db.query(AppConfig).all()
    
    # Default settings fallback (In case Admin hasn't set them yet)
    app_settings = {
        "terms_version": TERMS_VERSION,
        "maintenance_mode": False,    # True/False
        "app_version": "1.0.0",
        "support_email": "support@example.com",
        "min_withdrawal": 10.0
    }

    # Override defaults with actual DB values if they exist
    for config in configs:
        if config.config_key == "MAINTENANCE_MODE":
            app_settings["maintenance_mode"] = config.config_value.get("status", False)
        elif config.config_key == "APP_SETTINGS":
            # Merge other settings stored as JSON
            app_settings.update(config.config_value)
            app_settings["terms_version"] = TERMS_VERSION  # always the server value

    from routers.setup import get_profile
    prof = get_profile(db)
    app_settings.update({"support_email": prof["support_email"], "min_withdrawal": prof["min_withdrawal"],
                         "min_deposit": prof["min_deposit"], "company_name": prof["company_name"]})

    # 3. Return the complete payload to the frontend
    return {
        "status": "success",
        "settings": app_settings,
        "widgets": widget_list
    }


# ==========================================
# 2. HEALTH CHECK FOR MAINTENANCE
# ==========================================

@router.get("/status", response_model=Dict[str, Any])
def get_system_status(db: Session = Depends(get_db)):
    """
    Lightweight endpoint to check if the system is under maintenance.
    Useful for mobile apps to check before allowing login.
    """
    maintenance = db.query(AppConfig).filter(AppConfig.config_key == "MAINTENANCE_MODE").first()
    is_maintenance = maintenance.config_value.get("status", False) if maintenance else False

    return {
        "is_maintenance": is_maintenance,
        "message": "System is under maintenance. Please try again later." if is_maintenance else "System is running normally."
    }


# ==========================================
# 3. LEGAL VERSION (public, used by the signup page)
# ==========================================

@router.get("/legal", response_model=Dict[str, Any])
def get_legal_info():
    return {"terms_version": TERMS_VERSION, "documents": ["/terms", "/privacy", "/risk"]}

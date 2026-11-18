from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import SubscriptionPlan, UserSubscription, User
from auth import get_current_user
from schemas import SubscriptionPlanResponse

router = APIRouter()


# ==========================================
# 1. GET ALL PLANS (Public - no auth needed)
# ==========================================

@router.get("/plans", response_model=List[SubscriptionPlanResponse])
def get_all_plans(db: Session = Depends(get_db)):
    """
    Get all active subscription plans.
    This is a public endpoint so users can see plans before subscribing.
    """
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.price.asc()).all()
    
    return plans


# ==========================================
# 2. GET USER'S CURRENT SUBSCRIPTION
# ==========================================

@router.get("/current")
def get_current_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the user's active subscription details.
    Returns 404 if no active subscription exists.
    """
    sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.is_active == True
    ).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {
        "plan_id": str(sub.plan_id),
        "plan_name": plan.plan_name,
        "start_date": sub.start_date,
        "end_date": sub.end_date,
        "is_active": sub.is_active,
    }


# ==========================================
# 3. GET SUBSCRIPTION HISTORY
# ==========================================

@router.get("/history")
def get_subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all past subscriptions for the current user.
    Useful for a "Billing History" section in profile.
    """
    subs = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id
    ).order_by(UserSubscription.start_date.desc()).all()
    
    result = []
    for sub in subs:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
        result.append({
            "id": str(sub.id),
            "plan_name": plan.plan_name if plan else "Unknown",
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "is_active": sub.is_active,
        })
    
    return result
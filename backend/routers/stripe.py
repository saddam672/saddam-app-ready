from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import stripe, os, logging

from database import get_db
from models import User, Wallet, Transaction, SubscriptionPlan, UserSubscription
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/create-payment-intent")
def create_payment_intent(amount: float, currency: str = "usd", purpose: str = "WALLET_TOPUP", plan_id: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if amount <= 0: raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    if purpose not in ["WALLET_TOPUP", "SUBSCRIPTION"]: raise HTTPException(status_code=400, detail="Invalid purpose")
    if purpose == "SUBSCRIPTION" and not plan_id: raise HTTPException(status_code=400, detail="Plan ID is required for subscription")
    if purpose == "SUBSCRIPTION":
        # never trust the price sent by the browser: always charge the plan's real price
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id, SubscriptionPlan.is_active == True).first()
        if not plan: raise HTTPException(status_code=404, detail="Plan not found")
        amount = float(plan.price)
    else:
        from routers.setup import get_profile
        min_dep = float(get_profile(db)["min_deposit"])
        if amount < min_dep: raise HTTPException(status_code=400, detail=f"Minimum deposit is ${min_dep:.2f}")
    try:
        intent = stripe.PaymentIntent.create(amount=int(round(amount * 100)), currency=currency, metadata={"user_id": str(current_user.id), "purpose": purpose, "plan_id": plan_id if plan_id else ""})
        new_tx = Transaction(user_id=current_user.id, amount=amount, transaction_type=purpose, status="PENDING", payment_gateway_id=intent.id)
        db.add(new_tx)
        db.commit()
        return {"client_secret": intent.client_secret, "payment_intent_id": intent.id}
    except Exception as e:
        logger.error(f"Stripe Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create payment intent")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: Session = Depends(get_db)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except ValueError: raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError: raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'payment_intent.succeeded':
        await handle_successful_payment(event['data']['object'], db)
    elif event['type'] == 'payment_intent.payment_failed':
        tx = db.query(Transaction).filter(Transaction.payment_gateway_id == event['data']['object']['id']).first()
        if tx: tx.status = "FAILED"; db.commit()
    return {"status": "success"}

@router.get("/verify-payment/{intent_id}")
def verify_payment(intent_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.payment_gateway_id == intent_id).first()
    if not tx: raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": tx.status, "amount": float(tx.amount), "type": tx.transaction_type}

async def handle_successful_payment(payment_intent: dict, db: Session):
    tx = db.query(Transaction).filter(Transaction.payment_gateway_id == payment_intent['id'], Transaction.status == 'PENDING').first()
    if not tx: return
    tx.status = "SUCCESS"
    metadata = payment_intent.get('metadata', {})
    purpose = metadata.get('purpose')
    
    user = db.query(User).filter(User.id == tx.user_id).first()
    if user: user.has_deposited = True # <--- নতুন লাইন: ডিপোজিট করলে আনলক হবে
    
    if purpose == "WALLET_TOPUP":
        wallet = db.query(Wallet).filter(Wallet.user_id == tx.user_id).first()
        if wallet: wallet.real_balance += tx.amount; wallet.updated_at = datetime.now(timezone.utc)
    elif purpose == "SUBSCRIPTION":
        plan_id = metadata.get('plan_id')
        if plan_id:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
            if plan:
                existing_sub = db.query(UserSubscription).filter(UserSubscription.user_id == tx.user_id, UserSubscription.is_active == True).first()
                if existing_sub: existing_sub.is_active = False
                new_sub = UserSubscription(user_id=tx.user_id, plan_id=plan.id, start_date=datetime.now(timezone.utc), end_date=datetime.now(timezone.utc) + timedelta(days=plan.duration_days), is_active=True)
                db.add(new_sub)
    db.commit()
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import logging, os

from database import get_db
from models import User, UserApiKey
from schemas import UserApiKeyCreate, UserApiKeyResponse
from auth import get_current_user, require_trading_consent
from security import encrypt_data, decrypt_data

# লগার সেটআপ (এরর ট্র্যাক করার জন্য)
logger = logging.getLogger(__name__)

router = APIRouter()

# Only these pairs can be traded through the app (edit via ALLOWED_SYMBOLS env var, comma separated)
ALLOWED_SYMBOLS = set(os.getenv("ALLOWED_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT").upper().split(","))

# ==========================================
# 1. SAVE & RETRIEVE API KEYS (Encrypted)
# ==========================================

@router.post("/api-keys", response_model=UserApiKeyResponse, status_code=status.HTTP_201_CREATED)
def save_binance_api_keys(
    api_data: UserApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Saves the user's Binance API and Secret keys.
    The keys are encrypted using AES-256 before saving to the database.
    """
    # Check if user already has API keys saved
    existing_key = db.query(UserApiKey).filter(
        UserApiKey.user_id == current_user.id,
        UserApiKey.exchange_name == 'BINANCE'
    ).first()

    # Encrypt the keys
    encrypted_api = encrypt_data(api_data.api_key)
    encrypted_secret = encrypt_data(api_data.secret_key)

    if existing_key:
        # Update existing keys
        existing_key.api_key_encrypted = encrypted_api
        existing_key.secret_key_encrypted = encrypted_secret
        existing_key.is_active = True
        db.commit()
        db.refresh(existing_key)
        return existing_key
    else:
        # Create new API key entry
        new_key = UserApiKey(
            user_id=current_user.id,
            exchange_name='BINANCE',
            api_key_encrypted=encrypted_api,
            secret_key_encrypted=encrypted_secret,
            is_active=True
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        return new_key


# Helper function to get Binance Client for a user
def get_binance_client(user_id: str, db: Session) -> Client:
    """Fetches encrypted keys, decrypts them, and returns an authenticated Binance Client."""
    api_key_record = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id,
        UserApiKey.is_active == True
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=400, 
            detail="Binance API keys not found. Please add them in Settings."
        )

    # Decrypt keys
    api_key = decrypt_data(api_key_record.api_key_encrypted)
    secret_key = decrypt_data(api_key_record.secret_key_encrypted)

    # Controlled by BINANCE_TESTNET in .env (true = Binance testnet, no real money; false = REAL trading)
    use_testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    return Client(api_key, secret_key, testnet=use_testnet)


# ==========================================
# 2. CHECK ACCOUNT BALANCE
# ==========================================

@router.get("/balance")
def get_binance_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the live spot wallet balance from Binance.
    """
    try:
        client = get_binance_client(current_user.id, db)
        account_info = client.get_account()
        
        # Filter out zero balances to keep response clean
        balances = [
            {
                "asset": b["asset"], 
                "free": float(b["free"]), 
                "locked": float(b["locked"])
            } 
            for b in account_info["balances"] 
            if float(b["free"]) > 0 or float(b["locked"]) > 0
        ]
        
        return {"status": "success", "balances": balances}

    except HTTPException:
        raise   # e.g. "keys not found" stays a clear 400, not a 500
    except BinanceAPIException as e:
        logger.error(f"Binance API Error: {e.message}")
        raise HTTPException(status_code=400, detail=f"Binance Error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        raise HTTPException(status_code=502, detail="Could not reach Binance right now. Check your connection and try again.")


# ==========================================
# 3. PLACE ORDER (Auto-Copy Trading)
# ==========================================

@router.post("/order")
def place_binance_order(
    symbol: str,          # e.g., "BTCUSDT"
    side: str,            # "BUY" or "SELL"
    order_type: str,      # "MARKET" or "LIMIT"
    quantity: float,
    price: float = None,  # Required for LIMIT orders
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trading_consent)   # <-- trading ONLY if the user gave permission
):
    """
    Places an order on the user's own Binance account.
    Allowed ONLY when the user accepted the current Terms and turned trading permission ON.
    """
    symbol = symbol.upper().strip()
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"Symbol not allowed. Allowed: {', '.join(sorted(ALLOWED_SYMBOLS))}")
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    try:
        client = get_binance_client(current_user.id, db)
        
        # Validate side and type
        side = side.upper()
        order_type = order_type.upper()

        if side not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="Side must be BUY or SELL")

        if order_type == "MARKET":
            order = client.order_market(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
        elif order_type == "LIMIT":
            if not price:
                raise HTTPException(
                    status_code=400, 
                    detail="Price is required for LIMIT orders"
                )
            order = client.order_limit(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=str(price)
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid order type. Use MARKET or LIMIT."
            )

        return {
            "status": "success",
            "message": f"{side} order placed successfully",
            "order_details": order
        }

    except HTTPException:
        raise
    except BinanceOrderException as e:
        logger.error(f"Binance Order Error: {e.message}")
        raise HTTPException(status_code=400, detail=f"Order Failed: {e.message}")
    except BinanceAPIException as e:
        logger.error(f"Binance API Error: {e.message}")
        raise HTTPException(status_code=400, detail=f"API Error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to place order")


# ==========================================
# 4. GET LIVE PRICES (Public API)
# ==========================================

@router.get("/prices")
def get_live_prices(symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT"):
    """
    Fetches live ticker prices for specified symbols.
    Does not require user API keys (Public Binance API).
    """
    try:
        # For public data, we don't need user keys
        public_client = Client()
        prices = {}
        
        for symbol in symbols.split(","):
            ticker = public_client.get_symbol_ticker(symbol=symbol.strip().upper())
            prices[ticker["symbol"]] = float(ticker["price"])
            
        return {"status": "success", "prices": prices}
        
    except Exception as e:
        logger.error(f"Public API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch live prices")
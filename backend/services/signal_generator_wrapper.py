"""
Signal Generator Wrapper - EXACT MATCH WITH STREAMLIT CODE
All logic (RSI, MACD, EMA, BB, Vol Profile, MTF) is preserved.
"""
import requests
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from models import TradingSignal
import logging
import concurrent.futures
from enum import Enum
from services.generator_jobs import update_job

logger = logging.getLogger(__name__)


# ============================================================
# 1. MARKET REGIME DETECTOR (Original)
# ============================================================
class MarketRegime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"

class MarketRegimeDetector:
    def __init__(self, adx_threshold=25, sma_period=20):
        self.adx_threshold = adx_threshold
        self.sma_period = sma_period

    def detect(self, df):
        try:
            adx = self._calculate_adx(df)
            sma = df['close'].rolling(self.sma_period).mean()
            sma_slope = sma.iloc[-1] - sma.iloc[-2] if len(sma) >= 2 else 0
            if adx > self.adx_threshold:
                return MarketRegime.BULL if sma_slope > 0 else MarketRegime.BEAR
            else:
                return MarketRegime.SIDEWAYS
        except:
            return MarketRegime.SIDEWAYS

    def _calculate_adx(self, df, period=14):
        try:
            high, low, close = df['high'], df['low'], df['close']
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean().iloc[-1]
            up_move = high.diff()
            down_move = -low.diff()
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr if atr != 0 else 0
            minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr if atr != 0 else 0
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) != 0 else 0
            return dx.rolling(period).mean().iloc[-1]
        except:
            return 20


# ============================================================
# 2. INDICATORS (Original)
# ============================================================
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    if rs.iloc[-1] == 0 or pd.isna(rs.iloc[-1]):
        return 50
    return 100 - (100 / (1 + rs.iloc[-1]))

def calculate_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def calculate_bb(df, period=20):
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    return sma.iloc[-1] + 2 * std.iloc[-1], sma.iloc[-1] - 2 * std.iloc[-1]

def calculate_volume_profile_poc(df, num_levels=20):
    try:
        price_min = df['low'].min()
        price_max = df['high'].max()
        if price_max == price_min:
            return df['close'].iloc[-1]
        step = (price_max - price_min) / num_levels
        levels = np.arange(price_min, price_max + step, step)
        volumes = []
        for i in range(len(levels) - 1):
            mask = (df['close'] >= levels[i]) & (df['close'] < levels[i + 1])
            volumes.append(df.loc[mask, 'volume'].sum())
        if not volumes or max(volumes) == 0:
            return df['close'].iloc[-1]
        poc_idx = np.argmax(volumes)
        return (levels[poc_idx] + levels[poc_idx + 1]) / 2
    except:
        return df['close'].iloc[-1]

def calculate_atr(df, period=14):
    try:
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
    except:
        return (df['high'].iloc[-1] - df['low'].iloc[-1]) * 0.5


# ============================================================
# 3. VOTING SYSTEM (Original)
# ============================================================
def voting_signal(df):
    vote_items = []
    votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
    
    # ১. RSI
    try:
        rsi = calculate_rsi(df)
        if rsi < 30: v = 'BUY'
        elif rsi > 70: v = 'SELL'
        else: v = 'HOLD'
        vote_items.append({'name': 'RSI', 'vote': v, 'value': f"{rsi:.1f}"})
        votes[v] += 1
    except:
        votes['HOLD'] += 1

    # ২. MACD
    try:
        macd_line, signal_line = calculate_macd(df)
        v = 'BUY' if macd_line > signal_line else 'SELL'
        vote_items.append({'name': 'MACD', 'vote': v, 'value': f"{macd_line:.4f}"})
        votes[v] += 1
    except:
        votes['HOLD'] += 1

    # ৩. EMA ক্রস (২০/৫০)
    try:
        ema_short = df['close'].ewm(span=20).mean().iloc[-1]
        ema_long = df['close'].ewm(span=50).mean().iloc[-1]
        v = 'BUY' if ema_short > ema_long else 'SELL'
        vote_items.append({'name': 'EMA(20/50)', 'vote': v, 'value': f"{ema_short:.2f}/{ema_long:.2f}"})
        votes[v] += 1
    except:
        votes['HOLD'] += 1

    # ৪. Bollinger Bands
    try:
        upper, lower = calculate_bb(df)
        last_price = df['close'].iloc[-1]
        if last_price <= lower: v = 'BUY'
        elif last_price >= upper: v = 'SELL'
        else: v = 'HOLD'
        vote_items.append({'name': 'Bollinger', 'vote': v, 'value': f"U:{upper:.2f} L:{lower:.2f}"})
        votes[v] += 1
    except:
        votes['HOLD'] += 1

    # ৫. Volume Profile (POC)
    try:
        poc = calculate_volume_profile_poc(df)
        last_price = df['close'].iloc[-1]
        if last_price > poc: v = 'BUY'
        elif last_price < poc: v = 'SELL'
        else: v = 'HOLD'
        vote_items.append({'name': 'Vol Profile', 'vote': v, 'value': f"POC: {poc:.4f}"})
        votes[v] += 1
    except:
        votes['HOLD'] += 1

    # সিদ্ধান্ত
    if votes['BUY'] >= 3: final_signal = 'BUY'
    elif votes['SELL'] >= 3: final_signal = 'SELL'
    else: final_signal = 'HOLD'

    return final_signal, votes, vote_items


# ============================================================
# 4. FETCH KLINES & PAIRS (Original)
# ============================================================
def fetch_klines(symbol, interval="1h", limit=100):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except:
        return None

def get_all_usdt_pairs(min_volume_usdt=1000000):
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        usdt_pairs = []
        for item in data:
            symbol = item['symbol']
            if symbol.endswith('USDT'):
                if any(x in symbol for x in ['UP', 'DOWN', 'BEAR', 'BULL', 'USDC', 'BUSD', 'DAI', 'TUSD']):
                    continue
                try:
                    volume = float(item['quoteVolume'])
                    if volume < min_volume_usdt:
                        continue
                    usdt_pairs.append({
                        'symbol': symbol,
                        'volume': volume,
                        'price': float(item['lastPrice'])
                    })
                except:
                    continue
        usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
        return usdt_pairs
    except:
        return []


# ============================================================
# 5. GENERATE SIGNAL (Original with MTF)
# ============================================================
def generate_signal(df, current_tf="1h", symbol=None, use_mtf=True):
    try:
        final_signal, votes, vote_items = voting_signal(df)
        
        mtf_score = 0
        if use_mtf and current_tf in ["1h", "2h", "4h"] and symbol:
            try:
                df_h4 = fetch_klines(symbol, interval="4h", limit=50)
                if df_h4 is not None and len(df_h4) > 30:
                    regime_h4 = MarketRegimeDetector().detect(df_h4)
                    if regime_h4 == MarketRegime.BULL: mtf_score += 1
                    elif regime_h4 == MarketRegime.BEAR: mtf_score -= 1
                
                df_d1 = fetch_klines(symbol, interval="1d", limit=30)
                if df_d1 is not None and len(df_d1) > 20:
                    regime_d1 = MarketRegimeDetector().detect(df_d1)
                    if regime_d1 == MarketRegime.BULL: mtf_score += 1
                    elif regime_d1 == MarketRegime.BEAR: mtf_score -= 1
            except:
                pass

        if final_signal == 'BUY' and mtf_score <= -2:
            final_signal = 'HOLD'
        elif final_signal == 'SELL' and mtf_score >= 2:
            final_signal = 'HOLD'

        last_price = df['close'].iloc[-1]
        current_atr = calculate_atr(df)
        
        if final_signal == "SELL":
            stop_loss = last_price + (current_atr * 1.8)
            take_profit = last_price - (current_atr * 3.5)
        else:
            stop_loss = last_price - (current_atr * 1.8)
            take_profit = last_price + (current_atr * 3.5)
        
        tp_percent = abs((take_profit - last_price) / last_price) * 100
        MIN_TP = 3.0
        if tp_percent < MIN_TP:
            if final_signal == "SELL":
                take_profit = last_price * (1 - MIN_TP/100)
            else:
                take_profit = last_price * (1 + MIN_TP/100)
        
        return {
            "signal": final_signal,
            "entry_price": float(last_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "reason": f"MTF স্কোর: {mtf_score}"
        }
    except Exception as e:
        return None


# ============================================================
# 6. PROCESS PAIR
# ============================================================
def process_pair(pair, interval="1h", use_mtf=True):
    symbol = pair['symbol']
    df = fetch_klines(symbol, interval=interval, limit=100)
    
    if df is not None and len(df) > 50:
        sig = generate_signal(df, current_tf=interval, symbol=symbol, use_mtf=use_mtf)
        if sig and sig['signal'] in ('BUY', 'SELL'):
            return {
                "pair": symbol,
                "signal_type": sig['signal'],
                "entry_price": sig['entry_price'],
                "target_price": sig['take_profit'],
                "stop_loss": sig['stop_loss'],
            }
    return None


# ============================================================
# 7. RUN GENERATOR
# ============================================================
def run_signal_generator(
    db: Session,
    max_pairs: int = 500,
    interval: str = "1h",
    min_volume_usdt: int = 1000000, # Exactly matching Streamlit
    use_mtf: bool = True,
    max_workers: int = 10,
    job_id: str = None,
) -> dict:
    result = {"signals_created": 0, "signals_failed": 0, "pairs_scanned": 0}

    try:
        if job_id: update_job(job_id, status="running")

        logger.info(f"Fetching pairs (min volume: {min_volume_usdt})...")
        all_pairs = get_all_usdt_pairs(min_volume_usdt=min_volume_usdt)

        if not all_pairs:
            if job_id: update_job(job_id, status="error", error="No pairs fetched")
            return result

        pairs_to_scan = all_pairs[:max_pairs]
        total = len(pairs_to_scan)
        result["pairs_scanned"] = total

        if job_id: update_job(job_id, pairs_total=total)

        signals_to_save = []
        completed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_pair, pair, interval, use_mtf): pair
                for pair in pairs_to_scan
            }

            for future in concurrent.futures.as_completed(futures):
                pair = futures[future]
                completed += 1
                try:
                    sig_data = future.result()
                    if sig_data:
                        signals_to_save.append(sig_data)
                except Exception as e:
                    result["signals_failed"] += 1

                if job_id:
                    update_job(
                        job_id,
                        pairs_scanned=completed,
                        last_completed=pair['symbol'],
                        signals_found=len(signals_to_save),
                    )

        if job_id: update_job(job_id, current_pair="Saving to database...")

        for sig_data in signals_to_save:
            try:
                new_signal = TradingSignal(
                    pair=sig_data["pair"],
                    signal_type=sig_data["signal_type"],
                    entry_price=sig_data["entry_price"],
                    target_price=sig_data["target_price"],
                    stop_loss=sig_data["stop_loss"],
                    status="ACTIVE",
                )
                db.add(new_signal)
                result["signals_created"] += 1
            except Exception as e:
                result["signals_failed"] += 1

        db.commit()

        log_msg = f"✅ Scanned {total} pairs. Found {len(signals_to_save)} signals. Saved {result['signals_created']}."
        result["log"] = log_msg

        if job_id:
            update_job(
                job_id, status="done", signals_created=result["signals_created"],
                signals_failed=result["signals_failed"], current_pair="", log=log_msg
            )

    except Exception as e:
        logger.error(f"Generator crashed: {e}")
        if job_id: update_job(job_id, status="error", error=str(e))

    return result
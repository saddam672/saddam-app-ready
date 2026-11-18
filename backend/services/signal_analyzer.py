"""Advanced Signal Analyzer - Exact Logic from Streamlit (Bug-Free)"""
from sqlalchemy.orm import Session
from models import TradingSignal
import logging
import requests
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def fetch_klines(symbol, interval="1h", limit=100):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        resp = requests.get(url, timeout=5)
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
    except Exception as e:
        logger.error(f"Fetch error for {symbol}: {e}")
        return None

# ============================================================
# 1. Exact Support/Resistance Logic from your code
# ============================================================
def calculate_support_resistance(df, lookback=30, num_levels=3):
    try:
        data = df.tail(lookback)
        highs = data['high'].values
        lows = data['low'].values
        pivot_highs = []
        pivot_lows = []
        for i in range(2, len(data)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                pivot_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                pivot_lows.append(lows[i])
        def cluster(values, tolerance=0.001):
            if not values: return []
            values = sorted(values)
            clusters = []
            current_cluster = [values[0]]
            for v in values[1:]:
                if abs(v - current_cluster[-1]) / current_cluster[-1] < tolerance:
                    current_cluster.append(v)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [v]
            clusters.append(np.mean(current_cluster))
            return clusters
        resistance = cluster(pivot_highs)[-num_levels:] if pivot_highs else []
        support = cluster(pivot_lows)[-num_levels:] if pivot_lows else []
        if len(resistance) < num_levels:
            resistance = [np.percentile(highs, 80), np.percentile(highs, 90), np.percentile(highs, 95)]
        if len(support) < num_levels:
            support = [np.percentile(lows, 20), np.percentile(lows, 10), np.percentile(lows, 5)]
        return support[:num_levels], resistance[:num_levels]
    except:
        return [df['low'].quantile(0.2), df['low'].quantile(0.1), df['low'].quantile(0.05)], \
               [df['high'].quantile(0.8), df['high'].quantile(0.9), df['high'].quantile(0.95)]

# ============================================================
# 2. Exact Entry Zone Logic from your code
# ============================================================
def get_price_trigger_zone(price, support, resistance):
    try:
        nearest_support = max([s for s in support if s < price], default=None)
        nearest_resistance = min([r for r in resistance if r > price], default=None)
    except:
        nearest_support, nearest_resistance = None, None
    
    zone = "NEUTRAL"
    details = ""
    
    if nearest_support:
        diff_pct = abs((price - nearest_support) / price) * 100
        if diff_pct < 1.0:
            zone = "BUY ZONE"
            details = f"Price is {diff_pct:.2f}% above nearest Support. High bounce probability."
        elif diff_pct < 2.0:
            zone = "NEAR SUPPORT"
            details = f"Price is {diff_pct:.2f}% above Support. Monitor closely."
    
    if nearest_resistance:
        diff_pct = abs((nearest_resistance - price) / price) * 100
        if diff_pct < 1.0:
            zone = "SELL ZONE"
            details = f"Price is {diff_pct:.2f}% below nearest Resistance. High rejection probability."
        elif diff_pct < 2.0:
            zone = "NEAR RESISTANCE"
            details = f"Price is {diff_pct:.2f}% below Resistance. Watch for breakout."
    
    if zone == "NEUTRAL":
        details = "Price is far from Support/Resistance. No trigger zone currently."
    
    return zone, details, nearest_support, nearest_resistance

# ============================================================
# 3. Exact Trendline Logic from your code
# ============================================================
def calculate_trendline_status(df, order=5, lookback=50):
    try:
        data = df.tail(lookback).copy()
        data = data.reset_index(drop=True)
        highs = data['high'].values
        lows = data['low'].values
        
        pivot_lows = []
        for i in range(order, len(data) - order):
            if lows[i] == min(lows[i-order:i+order+1]):
                pivot_lows.append((i, lows[i]))
        pivot_highs = []
        for i in range(order, len(data) - order):
            if highs[i] == max(highs[i-order:i+order+1]):
                pivot_highs.append((i, highs[i]))
        
        uptrend_active = False
        if len(pivot_lows) >= 2:
            p1, p2 = pivot_lows[-2], pivot_lows[-1]
            x1, y1 = p1
            x2, y2 = p2
            if x2 > x1 and y2 > y1:
                slope = (y2 - y1) / (x2 - x1)
                end_x = len(data) - 1
                y_end = y1 + slope * (end_x - x1)
                if y1 < y_end: 
                    uptrend_active = True

        downtrend_active = False
        if len(pivot_highs) >= 2:
            p1, p2 = pivot_highs[-2], pivot_highs[-1]
            x1, y1 = p1
            x2, y2 = p2
            if x2 > x1 and y2 < y1:
                slope = (y2 - y1) / (x2 - x1)
                end_x = len(data) - 1
                y_end = y1 + slope * (end_x - x1)
                if y1 > y_end: 
                    downtrend_active = True
                    
        if uptrend_active: return "Uptrend Line (Active)"
        if downtrend_active: return "Downtrend Line (Active)"
        return "Range Bound (No Trendline)"
    except:
        return "Range Bound"

# ============================================================
# 4. Candlestick Pattern
# ============================================================
def detect_candlestick_pattern(df):
    if len(df) < 2: return "N/A"
    last, prev = df.iloc[-1], df.iloc[-2]
    
    body = abs(last['close'] - last['open'])
    upper_wick = last['high'] - max(last['close'], last['open'])
    lower_wick = min(last['close'], last['open']) - last['low']
    candle_range = last['high'] - last['low']
    
    if candle_range == 0: return "Neutral"
    
    if body <= candle_range * 0.1: return "Doji (Indecision)"
    
    if lower_wick > (body * 2) and upper_wick < (body * 0.5):
        return "Hammer (Bullish Reversal)" if last['close'] < last['open'] else "Bullish Pin Bar"
    if upper_wick > (body * 2) and lower_wick < (body * 0.5):
        return "Shooting Star (Bearish Reversal)" if last['close'] > last['open'] else "Bearish Pin Bar"
        
    if prev['close'] < prev['open'] and last['close'] > last['open']:
        if last['close'] > prev['open'] and last['open'] < prev['close']:
            return "Bullish Engulfing"
            
    if prev['close'] > prev['open'] and last['close'] < last['open']:
        if last['close'] < prev['open'] and last['open'] > prev['close']:
            return "Bearish Engulfing"

    return "Neutral / No Clear Pattern"

# ============================================================
# 5. Main Analyzer (Fully Guarded against crashes)
# ============================================================
def analyze_all_signals(db: Session) -> dict:
    signals = db.query(TradingSignal).filter(TradingSignal.status == "ACTIVE").all()
    analyzed = 0
    
    for sig in signals:
        try:
            df = fetch_klines(sig.pair, interval="1h", limit=100)
            if df is None or len(df) < 30: 
                continue
                
            current_price = float(sig.entry_price) if sig.entry_price else float(df['close'].iloc[-1])
            
            # Get Exact Logics
            sup_levels, res_levels = calculate_support_resistance(df)
            zone, zone_details, near_sup, near_res = get_price_trigger_zone(current_price, sup_levels, res_levels)
            chart_pat = calculate_trendline_status(df)
            candle_pat = detect_candlestick_pattern(df)
            
            # Safe Formatting (handles None values)
            sup_str = f"{near_sup:.6f}" if near_sup is not None else "N/A"
            res_str = f"{near_res:.6f}" if near_res is not None else "N/A"
            
            details = (
                f"Candle: {candle_pat}\n"
                f"Trend: {chart_pat}\n"
                f"Zone: {zone}\n"
                f"Nearest Support: {sup_str}\n"
                f"Nearest Resistance: {res_str}\n"
                f"Note: {zone_details}"
            )
            
            # Save to DB
            sig.candle_pattern = candle_pat
            sig.chart_pattern = chart_pat
            sig.support_level = near_sup
            sig.resistance_level = near_res
            sig.entry_zone = zone
            sig.analysis_details = details
            
            # Score calculation based on user's zone logic
            score = 50
            if sig.signal_type == "BUY":
                if zone == "BUY ZONE": score += 30
                elif zone == "NEAR SUPPORT": score += 15
                elif zone == "SELL ZONE": score -= 20
                
                if "Bullish" in candle_pat: score += 10
                if "Uptrend" in chart_pat: score += 10
                
            elif sig.signal_type == "SELL":
                if zone == "SELL ZONE": score += 30
                elif zone == "NEAR RESISTANCE": score += 15
                elif zone == "BUY ZONE": score -= 20
                
                if "Bearish" in candle_pat: score += 10
                if "Downtrend" in chart_pat: score += 10
            
            sig.effectiveness_score = max(0, min(100, score))
            sig.effectiveness_reason = details
            
            analyzed += 1
        except Exception as e:
            logger.error(f"Analysis failed for {sig.pair}: {e}")
            
    db.commit()
    return {"analyzed": analyzed, "total_active": len(signals)}
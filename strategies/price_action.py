"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ESTRATEGIA PRICE ACTION v5.2                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from config import PA_MIN_CANDLE_BODY_PIPS, PA_MAX_WICK_RATIO


class PriceActionSystem:
    """Sistema de Trading basado en Price Action"""
    
    def __init__(self):
        self.enabled = True
        self.min_candle_body_pips = PA_MIN_CANDLE_BODY_PIPS
        self.max_wick_ratio = PA_MAX_WICK_RATIO
    
    def is_bullish_engulfing(self, df):
        """Detecta patrón Bullish Engulfing"""
        if len(df) < 2:
            return False
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Vela anterior bajista
        prev_bearish = previous['close'] < previous['open']
        
        # Vela actual alcista
        curr_bullish = current['close'] > current['open']
        
        # Vela actual envuelve a la anterior
        engulfs = (current['open'] <= previous['close'] and 
                  current['close'] >= previous['open'])
        
        # Tamaño significativo
        body_size = abs(current['close'] - current['open']) / 0.01
        significant = body_size > self.min_candle_body_pips
        
        return prev_bearish and curr_bullish and engulfs and significant
    
    def is_bearish_engulfing(self, df):
        """Detecta patrón Bearish Engulfing"""
        if len(df) < 2:
            return False
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Vela anterior alcista
        prev_bullish = previous['close'] > previous['open']
        
        # Vela actual bajista
        curr_bearish = current['close'] < current['open']
        
        # Vela actual envuelve a la anterior
        engulfs = (current['open'] >= previous['close'] and 
                  current['close'] <= previous['open'])
        
        # Tamaño significativo
        body_size = abs(current['close'] - current['open']) / 0.01
        significant = body_size > self.min_candle_body_pips
        
        return prev_bullish and curr_bearish and engulfs and significant
    
    def is_hammer(self, df):
        """Detecta patrón Hammer (alcista)"""
        if len(df) < 1:
            return False
        
        candle = df.iloc[-1]
        
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        # Cuerpo pequeño en la parte superior
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return False
        
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        
        # Mecha inferior al menos 2x el cuerpo
        hammer_condition = (lower_wick >= body * 2 and 
                          upper_wick < body * 0.5 and
                          body / 0.01 > 5)
        
        return hammer_condition
    
    def is_shooting_star(self, df):
        """Detecta patrón Shooting Star (bajista)"""
        if len(df) < 1:
            return False
        
        candle = df.iloc[-1]
        
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return False
        
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        
        # Mecha superior al menos 2x el cuerpo
        star_condition = (upper_wick >= body * 2 and 
                         lower_wick < body * 0.5 and
                         body / 0.01 > 5)
        
        return star_condition
    
    def get_signal(self, df):
        """Genera señal basada en Price Action"""
        if not self.enabled:
            return None
        
        if len(df) < 3:
            return None
        
        # Detectar patrones alcistas
        if self.is_bullish_engulfing(df):
            return {
                'signal': 1,
                'confidence': 0.70,
                'reason': "Price Action: Bullish Engulfing",
                'sl_pips': 35,
                'tp_pips': 90,
                'pattern': 'bullish_engulfing'
            }
        
        if self.is_hammer(df):
            return {
                'signal': 1,
                'confidence': 0.65,
                'reason': "Price Action: Hammer",
                'sl_pips': 30,
                'tp_pips': 80,
                'pattern': 'hammer'
            }
        
        # Detectar patrones bajistas
        if self.is_bearish_engulfing(df):
            return {
                'signal': -1,
                'confidence': 0.70,
                'reason': "Price Action: Bearish Engulfing",
                'sl_pips': 35,
                'tp_pips': 90,
                'pattern': 'bearish_engulfing'
            }
        
        if self.is_shooting_star(df):
            return {
                'signal': -1,
                'confidence': 0.65,
                'reason': "Price Action: Shooting Star",
                'sl_pips': 30,
                'tp_pips': 80,
                'pattern': 'shooting_star'
            }
        
        return None
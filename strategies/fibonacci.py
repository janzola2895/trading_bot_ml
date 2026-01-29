"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   ESTRATEGIA FIBONACCI RETRACEMENT v5.2                  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from config import FIBO_SWING_LOOKBACK, FIBO_MIN_SWING_PIPS


class FibonacciRetracementSystem:
    """Sistema de Trading basado en Fibonacci"""
    
    def __init__(self, swing_lookback=FIBO_SWING_LOOKBACK, 
                 min_swing_pips=FIBO_MIN_SWING_PIPS):
        self.swing_lookback = swing_lookback
        self.min_swing_pips = min_swing_pips
        self.enabled = True
        
        self.fib_levels = {
            '0.236': 0.236,
            '0.382': 0.382,
            '0.500': 0.500,
            '0.618': 0.618,
            '0.786': 0.786
        }
        
        self.cached_swing = None
        self.last_calculation = None
    
    def find_swing_points(self, df):
        """Encuentra puntos swing para Fibonacci"""
        if len(df) < self.swing_lookback:
            return None
        
        recent = df.tail(self.swing_lookback).copy()
        
        # Buscar swing high más reciente
        swing_high_idx = recent['high'].idxmax()
        swing_high = recent.loc[swing_high_idx, 'high']
        swing_high_time = recent.loc[swing_high_idx, 'time']
        
        # Buscar swing low más reciente
        swing_low_idx = recent['low'].idxmin()
        swing_low = recent.loc[swing_low_idx, 'low']
        swing_low_time = recent.loc[swing_low_idx, 'time']
        
        # Calcular distancia en pips
        swing_range_pips = abs(swing_high - swing_low) / 0.01
        
        if swing_range_pips < self.min_swing_pips:
            return None
        
        # Determinar tendencia (el punto más reciente define dirección)
        if swing_high_time > swing_low_time:
            trend = 'uptrend'
            swing_start = swing_low
            swing_end = swing_high
        else:
            trend = 'downtrend'
            swing_start = swing_high
            swing_end = swing_low
        
        return {
            'trend': trend,
            'swing_start': float(swing_start),
            'swing_end': float(swing_end),
            'swing_range': float(swing_range_pips),
            'high': float(swing_high),
            'low': float(swing_low)
        }
    
    def calculate_fib_levels(self, swing):
        """Calcula niveles de Fibonacci"""
        if not swing:
            return {}
        
        swing_start = swing['swing_start']
        swing_end = swing['swing_end']
        trend = swing['trend']
        
        levels = {}
        
        for name, ratio in self.fib_levels.items():
            if trend == 'uptrend':
                # En uptrend, retroceso desde high hacia low
                level_price = swing_end - (swing_end - swing_start) * ratio
            else:
                # En downtrend, retroceso desde low hacia high
                level_price = swing_end + (swing_start - swing_end) * ratio
            
            levels[name] = float(level_price)
        
        return levels
    
    def get_signal(self, df, current_price):
        """Genera señal basada en Fibonacci"""
        if not self.enabled:
            return None
        
        # Recalcular swing points cada 5 minutos
        now = datetime.now()
        if (self.last_calculation is None or 
            (now - self.last_calculation).total_seconds() > 300):
            
            self.cached_swing = self.find_swing_points(df)
            self.last_calculation = now
        
        swing = self.cached_swing
        
        if not swing:
            return None
        
        fib_levels = self.calculate_fib_levels(swing)
        
        if not fib_levels:
            return None
        
        # Buscar nivel Fibonacci cercano
        for level_name, level_price in fib_levels.items():
            distance_pips = abs(current_price - level_price) / 0.01
            
            if distance_pips < 15:  # Dentro de 15 pips del nivel
                
                if swing['trend'] == 'uptrend':
                    # En uptrend, comprar en retroceso
                    confidence = 0.60 + (float(level_name) * 0.15)
                    confidence = min(confidence, 0.80)
                    
                    return {
                        'signal': 1,
                        'confidence': confidence,
                        'reason': f"Fibo: Retroceso {level_name} en ${level_price:.2f} (Uptrend)",
                        'sl_pips': 40,
                        'tp_pips': 100,
                        'fib_level': level_name
                    }
                
                elif swing['trend'] == 'downtrend':
                    # En downtrend, vender en retroceso
                    confidence = 0.60 + (float(level_name) * 0.15)
                    confidence = min(confidence, 0.80)
                    
                    return {
                        'signal': -1,
                        'confidence': confidence,
                        'reason': f"Fibo: Retroceso {level_name} en ${level_price:.2f} (Downtrend)",
                        'sl_pips': 40,
                        'tp_pips': 100,
                        'fib_level': level_name
                    }
        
        return None
"""
╔══════════════════════════════════════════════════════════════════════════╗
║        ESTRATEGIA FIBONACCI RETRACEMENT v5.3 - MTF                       ║
║                                                                          ║
║  🆕 v5.3: Análisis Multi-Timeframe integrado                            ║
║  ✅ Identifica swings en múltiples temporalidades                       ║
║  ✅ Valida niveles con confluencia entre TFs                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
from datetime import datetime
from config import FIBO_SWING_LOOKBACK, FIBO_MIN_SWING_PIPS


class FibonacciRetracementSystem:
    """Sistema de Trading Fibonacci con Multi-Timeframe"""
    
    def __init__(self, symbol="XAUUSD", swing_lookback=FIBO_SWING_LOOKBACK, 
                 min_swing_pips=FIBO_MIN_SWING_PIPS):
        self.symbol = symbol
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
        
        # 🆕 MTF: Configuración de timeframes
        self.mtf_timeframes = {
            'M30': mt5.TIMEFRAME_M30,  # Principal
            'H1': mt5.TIMEFRAME_H1,    # Confirmación
            'H4': mt5.TIMEFRAME_H4     # Contexto mayor
        }
        
        # Cache
        self.cached_swing = None
        self.last_calculation = None
        
        # 🆕 Cache MTF
        self.mtf_swings = {}
        self.mtf_cache = {}
        self.last_mtf_update = {}
    
    def get_mtf_data(self, timeframe_name, bars=100):
        """Obtiene datos de un timeframe específico con cache"""
        now = datetime.now()
        cache_key = timeframe_name
        
        # Verificar cache (válido por 2 minutos)
        if cache_key in self.mtf_cache:
            last_update = self.last_mtf_update.get(cache_key)
            if last_update and (now - last_update).total_seconds() < 120:
                return self.mtf_cache[cache_key]
        
        # Obtener datos frescos
        timeframe = self.mtf_timeframes[timeframe_name]
        rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, bars)
        
        if rates is None or len(rates) == 0:
            return None
        
        import pandas as pd
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Actualizar cache
        self.mtf_cache[cache_key] = df
        self.last_mtf_update[cache_key] = now
        
        return df
    
    def find_swing_points(self, df):
        """Encuentra puntos swing para Fibonacci"""
        if len(df) < self.swing_lookback:
            return None
        
        recent = df.tail(self.swing_lookback).copy()
        
        # Buscar swing high
        swing_high_idx = recent['high'].idxmax()
        swing_high = recent.loc[swing_high_idx, 'high']
        swing_high_time = recent.loc[swing_high_idx, 'time']
        
        # Buscar swing low
        swing_low_idx = recent['low'].idxmin()
        swing_low = recent.loc[swing_low_idx, 'low']
        swing_low_time = recent.loc[swing_low_idx, 'time']
        
        # Calcular distancia
        swing_range_pips = abs(swing_high - swing_low) / 0.01
        
        if swing_range_pips < self.min_swing_pips:
            return None
        
        # Determinar tendencia
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
                level_price = swing_end - (swing_end - swing_start) * ratio
            else:
                level_price = swing_end + (swing_start - swing_end) * ratio
            
            levels[name] = float(level_price)
        
        return levels
    
    def analyze_mtf_swings(self):
        """
        🆕 Analiza swings en múltiples temporalidades
        
        Returns:
            dict: Swings por timeframe con confluencias
        """
        mtf_swings = {}
        
        for tf_name in ['M30', 'H1', 'H4']:
            df_tf = self.get_mtf_data(tf_name, bars=100)
            
            if df_tf is None or len(df_tf) < self.swing_lookback:
                mtf_swings[tf_name] = None
                continue
            
            swing = self.find_swing_points(df_tf)
            mtf_swings[tf_name] = swing
        
        return mtf_swings
    
    def check_mtf_confluence(self, current_price, mtf_swings):
        """
        🆕 Verifica confluencia de niveles Fibonacci entre TFs
        
        Args:
            current_price: Precio actual
            mtf_swings: Diccionario de swings por TF
        
        Returns:
            dict: Análisis de confluencia
        """
        confluence_analysis = {
            'has_confluence': False,
            'confluence_level': None,
            'aligned_tfs': [],
            'trend_agreement': False,
            'confidence_boost': 0.0
        }
        
        # Calcular niveles para cada TF
        all_levels = {}
        trends = []
        
        for tf_name, swing in mtf_swings.items():
            if swing is None:
                continue
            
            levels = self.calculate_fib_levels(swing)
            all_levels[tf_name] = levels
            trends.append(swing['trend'])
        
        if len(all_levels) == 0:
            return confluence_analysis
        
        # Buscar confluencias (niveles cercanos en diferentes TFs)
        tolerance_pips = 20  # Tolerancia para considerar confluencia
        
        for level_name in self.fib_levels.keys():
            prices_at_level = []
            tfs_at_level = []
            
            for tf_name, levels in all_levels.items():
                if level_name in levels:
                    prices_at_level.append(levels[level_name])
                    tfs_at_level.append(tf_name)
            
            if len(prices_at_level) < 2:
                continue
            
            # Verificar si los precios están cercanos
            price_range = max(prices_at_level) - min(prices_at_level)
            price_range_pips = price_range / 0.01
            
            if price_range_pips <= tolerance_pips:
                # Hay confluencia en este nivel
                avg_price = sum(prices_at_level) / len(prices_at_level)
                distance_to_current = abs(current_price - avg_price) / 0.01
                
                # Verificar si el precio está cerca del nivel
                if distance_to_current < 15:
                    confluence_analysis['has_confluence'] = True
                    confluence_analysis['confluence_level'] = level_name
                    confluence_analysis['aligned_tfs'] = tfs_at_level
                    
                    # Boost según número de TFs alineados
                    if len(tfs_at_level) == 3:
                        confluence_analysis['confidence_boost'] = 0.10
                    elif len(tfs_at_level) == 2:
                        confluence_analysis['confidence_boost'] = 0.05
                    
                    break
        
        # Verificar acuerdo de tendencias
        if len(trends) >= 2:
            unique_trends = set(trends)
            if len(unique_trends) == 1:
                confluence_analysis['trend_agreement'] = True
                confluence_analysis['confidence_boost'] += 0.05
        
        return confluence_analysis
    
    def get_signal(self, df, current_price):
        """Genera señal basada en Fibonacci con MTF"""
        if not self.enabled:
            return None
        
        # Recalcular cada 5 minutos
        now = datetime.now()
        if (self.last_calculation is None or 
            (now - self.last_calculation).total_seconds() > 300):
            
            # Swing local (M30)
            self.cached_swing = self.find_swing_points(df)
            self.last_calculation = now
            
            # 🆕 Analizar swings MTF
            self.mtf_swings = self.analyze_mtf_swings()
        
        swing = self.cached_swing
        
        if not swing:
            return None
        
        fib_levels = self.calculate_fib_levels(swing)
        
        if not fib_levels:
            return None
        
        # 🆕 Verificar confluencia MTF
        mtf_confluence = self.check_mtf_confluence(current_price, self.mtf_swings)
        
        # Buscar nivel cercano
        for level_name, level_price in fib_levels.items():
            distance_pips = abs(current_price - level_price) / 0.01
            
            if distance_pips < 15:
                
                base_confidence = 0.60 + (float(level_name) * 0.15)
                
                # 🆕 Aplicar boost MTF
                if mtf_confluence['has_confluence']:
                    base_confidence += mtf_confluence['confidence_boost']
                
                base_confidence = min(base_confidence, 0.85)
                
                # Construir razón
                reason = f"Fibo: Retroceso {level_name} @ ${level_price:.2f}"
                
                if mtf_confluence['has_confluence']:
                    aligned = '+'.join(mtf_confluence['aligned_tfs'])
                    reason += f" + MTF({aligned})"
                
                if swing['trend'] == 'uptrend':
                    return {
                        'signal': 1,
                        'confidence': base_confidence,
                        'reason': reason,
                        'sl_pips': 40,
                        'tp_pips': 100,
                        'fib_level': level_name,
                        'mtf_confluence': mtf_confluence
                    }
                
                elif swing['trend'] == 'downtrend':
                    return {
                        'signal': -1,
                        'confidence': base_confidence,
                        'reason': reason,
                        'sl_pips': 40,
                        'tp_pips': 100,
                        'fib_level': level_name,
                        'mtf_confluence': mtf_confluence
                    }
        
        return None
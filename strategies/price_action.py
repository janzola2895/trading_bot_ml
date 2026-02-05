"""
╔══════════════════════════════════════════════════════════════════════════╗
║              ESTRATEGIA PRICE ACTION v6.0 - MULTI-TIMEFRAME             ║
║                                                                          ║
║  🆕 v6.0: Análisis multi-temporalidad                                   ║
║  - Detecta patrones en M30, H1, H4                                      ║
║  - Mayor confianza cuando patrones coinciden en múltiples TFs           ║
║  - Validación de tendencia en temporalidades superiores                ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import PA_MIN_CANDLE_BODY_PIPS, PA_MAX_WICK_RATIO


class PriceActionSystem:
    """Sistema Price Action con análisis multi-temporalidad"""
    
    def __init__(self):
        self.enabled = True
        self.min_candle_body_pips = PA_MIN_CANDLE_BODY_PIPS
        self.max_wick_ratio = PA_MAX_WICK_RATIO
        
        # Multi-timeframe config
        self.timeframes = {
            'M30': {'tf': mt5.TIMEFRAME_M30, 'weight': 1.0, 'cache_seconds': 60},
            'H1': {'tf': mt5.TIMEFRAME_H1, 'weight': 1.3, 'cache_seconds': 120},
            'H4': {'tf': mt5.TIMEFRAME_H4, 'weight': 1.6, 'cache_seconds': 300}
        }
        
        self.cached_patterns = {}
        self.last_calculation = {}
        
        for tf_name in self.timeframes:
            self.cached_patterns[tf_name] = None
            self.last_calculation[tf_name] = None
    
    def get_timeframe_data(self, tf, bars=100, symbol="XAUUSD"):
        """Obtiene datos de temporalidad específica"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None:
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except:
            return None
    
    def is_bullish_engulfing(self, df):
        """Detecta Bullish Engulfing"""
        if len(df) < 2:
            return False, {}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        prev_bearish = previous['close'] < previous['open']
        curr_bullish = current['close'] > current['open']
        engulfs = (current['open'] <= previous['close'] and 
                  current['close'] >= previous['open'])
        
        body_size = abs(current['close'] - current['open']) / 0.01
        significant = body_size > self.min_candle_body_pips
        
        is_valid = prev_bearish and curr_bullish and engulfs and significant
        
        details = {
            'pattern': 'bullish_engulfing',
            'body_pips': body_size,
            'candle_range': (current['high'] - current['low']) / 0.01
        }
        
        return is_valid, details
    
    def is_bearish_engulfing(self, df):
        """Detecta Bearish Engulfing"""
        if len(df) < 2:
            return False, {}
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        prev_bullish = previous['close'] > previous['open']
        curr_bearish = current['close'] < current['open']
        engulfs = (current['open'] >= previous['close'] and 
                  current['close'] <= previous['open'])
        
        body_size = abs(current['close'] - current['open']) / 0.01
        significant = body_size > self.min_candle_body_pips
        
        is_valid = prev_bullish and curr_bearish and engulfs and significant
        
        details = {
            'pattern': 'bearish_engulfing',
            'body_pips': body_size,
            'candle_range': (current['high'] - current['low']) / 0.01
        }
        
        return is_valid, details
    
    def is_hammer(self, df):
        """Detecta Hammer"""
        if len(df) < 1:
            return False, {}
        
        candle = df.iloc[-1]
        
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return False, {}
        
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        
        hammer_condition = (lower_wick >= body * 2 and 
                          upper_wick < body * 0.5 and
                          body / 0.01 > 5)
        
        details = {
            'pattern': 'hammer',
            'lower_wick_pips': lower_wick / 0.01,
            'body_pips': body / 0.01
        }
        
        return hammer_condition, details
    
    def is_shooting_star(self, df):
        """Detecta Shooting Star"""
        if len(df) < 1:
            return False, {}
        
        candle = df.iloc[-1]
        
        open_price = candle['open']
        close_price = candle['close']
        high_price = candle['high']
        low_price = candle['low']
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        
        if total_range == 0:
            return False, {}
        
        lower_wick = min(open_price, close_price) - low_price
        upper_wick = high_price - max(open_price, close_price)
        
        star_condition = (upper_wick >= body * 2 and 
                         lower_wick < body * 0.5 and
                         body / 0.01 > 5)
        
        details = {
            'pattern': 'shooting_star',
            'upper_wick_pips': upper_wick / 0.01,
            'body_pips': body / 0.01
        }
        
        return star_condition, details
    
    def detect_patterns_in_timeframe(self, df):
        """Detecta todos los patrones en un dataframe"""
        patterns = []
        
        # Bullish patterns
        is_bull_eng, details = self.is_bullish_engulfing(df)
        if is_bull_eng:
            patterns.append({
                'signal': 1,
                'pattern': 'bullish_engulfing',
                'details': details
            })
        
        is_hammer, details = self.is_hammer(df)
        if is_hammer:
            patterns.append({
                'signal': 1,
                'pattern': 'hammer',
                'details': details
            })
        
        # Bearish patterns
        is_bear_eng, details = self.is_bearish_engulfing(df)
        if is_bear_eng:
            patterns.append({
                'signal': -1,
                'pattern': 'bearish_engulfing',
                'details': details
            })
        
        is_star, details = self.is_shooting_star(df)
        if is_star:
            patterns.append({
                'signal': -1,
                'pattern': 'shooting_star',
                'details': details
            })
        
        return patterns
    
    def analyze_all_timeframes(self, symbol="XAUUSD"):
        """Analiza patrones en todas las temporalidades"""
        now = datetime.now()
        all_patterns = {}
        
        for tf_name, tf_config in self.timeframes.items():
            # Verificar cache
            last_calc = self.last_calculation.get(tf_name)
            cache_time = tf_config['cache_seconds']
            
            if last_calc and (now - last_calc).total_seconds() < cache_time:
                all_patterns[tf_name] = self.cached_patterns[tf_name]
                continue
            
            # Obtener datos
            df = self.get_timeframe_data(tf_config['tf'], bars=50, symbol=symbol)
            if df is None or len(df) < 3:
                all_patterns[tf_name] = []
                continue
            
            # Detectar patrones
            patterns = self.detect_patterns_in_timeframe(df)
            
            # Añadir peso de temporalidad
            for pattern in patterns:
                pattern['timeframe'] = tf_name
                pattern['tf_weight'] = tf_config['weight']
            
            self.cached_patterns[tf_name] = patterns
            self.last_calculation[tf_name] = now
            all_patterns[tf_name] = patterns
        
        return all_patterns
    
    def find_pattern_confluence(self, all_patterns):
        """Encuentra patrones con confluencia multi-temporalidad"""
        if not all_patterns:
            return []
        
        # Recopilar todos los patrones
        all_flat = []
        for tf_name, patterns in all_patterns.items():
            all_flat.extend(patterns)
        
        if not all_flat:
            return []
        
        # Agrupar por dirección
        bullish_patterns = [p for p in all_flat if p['signal'] == 1]
        bearish_patterns = [p for p in all_flat if p['signal'] == -1]
        
        confluence = []
        
        # Analizar confluencia bullish
        if len(bullish_patterns) >= 2:
            timeframes = list(set(p['timeframe'] for p in bullish_patterns))
            patterns_names = [p['pattern'] for p in bullish_patterns]
            
            avg_weight = sum(p['tf_weight'] for p in bullish_patterns) / len(bullish_patterns)
            
            confluence.append({
                'signal': 1,
                'patterns': patterns_names,
                'timeframes': timeframes,
                'tf_count': len(timeframes),
                'weight': avg_weight,
                'all_patterns': bullish_patterns
            })
        
        # Analizar confluencia bearish
        if len(bearish_patterns) >= 2:
            timeframes = list(set(p['timeframe'] for p in bearish_patterns))
            patterns_names = [p['pattern'] for p in bearish_patterns]
            
            avg_weight = sum(p['tf_weight'] for p in bearish_patterns) / len(bearish_patterns)
            
            confluence.append({
                'signal': -1,
                'patterns': patterns_names,
                'timeframes': timeframes,
                'tf_count': len(timeframes),
                'weight': avg_weight,
                'all_patterns': bearish_patterns
            })
        
        return confluence
    
    def get_signal(self, df):
        """Genera señal basada en análisis multi-temporalidad"""
        if not self.enabled or len(df) < 3:
            return None
        
        # Analizar todas las temporalidades
        all_patterns = self.analyze_all_timeframes()
        
        # Buscar confluencias
        confluences = self.find_pattern_confluence(all_patterns)
        
        if not confluences:
            # No hay confluencia, buscar patrones individuales fuertes
            all_flat = []
            for tf_name, patterns in all_patterns.items():
                all_flat.extend(patterns)
            
            if not all_flat:
                return None
            
            # Priorizar por peso de temporalidad
            all_flat.sort(key=lambda x: x['tf_weight'], reverse=True)
            best_pattern = all_flat[0]
            
            # Confianza base para patrón individual
            if best_pattern['pattern'] in ['bullish_engulfing', 'bearish_engulfing']:
                confidence = 0.70
                sl_pips = 35
                tp_pips = 90
            else:  # hammer, shooting_star
                confidence = 0.65
                sl_pips = 30
                tp_pips = 80
            
            pattern_name = best_pattern['pattern'].replace('_', ' ').title()
            
            return {
                'signal': best_pattern['signal'],
                'confidence': confidence,
                'reason': f"Price Action: {pattern_name} ({best_pattern['timeframe']})",
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'pattern': best_pattern['pattern'],
                'timeframes': [best_pattern['timeframe']]
            }
        
        # Hay confluencia - señal más fuerte
        best_confluence = max(confluences, key=lambda x: (x['tf_count'], x['weight']))
        
        # Confianza según confluencia
        base_confidence = 0.72
        
        # Bonus por múltiples TFs
        tf_bonus = min((best_confluence['tf_count'] - 1) * 0.06, 0.15)
        
        confidence = base_confidence + tf_bonus
        confidence = min(confidence, 0.85)
        
        # Determinar SL/TP según patrón dominante
        dominant_pattern = best_confluence['patterns'][0]
        
        if 'engulfing' in dominant_pattern:
            sl_pips = 35
            tp_pips = 95
        else:
            sl_pips = 30
            tp_pips = 85
        
        tfs_text = '+'.join(sorted(best_confluence['timeframes']))
        patterns_text = ', '.join(set(p.replace('_', ' ').title() for p in best_confluence['patterns']))
        
        return {
            'signal': best_confluence['signal'],
            'confidence': confidence,
            'reason': f"Price Action MTF: {patterns_text} ({tfs_text})",
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'pattern': dominant_pattern,
            'timeframes': best_confluence['timeframes'],
            'tf_count': best_confluence['tf_count']
        }
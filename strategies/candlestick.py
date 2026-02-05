"""
╔══════════════════════════════════════════════════════════════════════════╗
║    ESTRATEGIA CANDLESTICK v5.3 - MTF + COOLDOWN INTERNO                 ║
║                                                                          ║
║  🆕 v5.3: Análisis Multi-Timeframe integrado                            ║
║  ✅ Confirma patrones en múltiples temporalidades                       ║
║  ✅ Sistema de cooldown interno (60 minutos)                            ║
║  ✅ Solo Engulfing patterns (evidencia científica 76%)                  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta

try:
    from config import (
        CS_MIN_BODY_PIPS, CS_MIN_CONFIDENCE, CS_MIN_ENGULF_RATIO,
        CS_REQUIRE_TREND_CONTEXT, CS_VOLUME_CONFIRMATION,
        CS_COOLDOWN_AFTER_SIGNAL_MINUTES, CS_MIN_CANDLES_BETWEEN_SIGNALS
    )
except ImportError:
    CS_MIN_BODY_PIPS = 15
    CS_MIN_CONFIDENCE = 0.60
    CS_MIN_ENGULF_RATIO = 2.0
    CS_REQUIRE_TREND_CONTEXT = True
    CS_VOLUME_CONFIRMATION = True
    CS_COOLDOWN_AFTER_SIGNAL_MINUTES = 90
    CS_MIN_CANDLES_BETWEEN_SIGNALS = 4


class CandlestickPatternSystem:
    """
    Sistema con Análisis Multi-Timeframe
    
    🆕 v5.3: Confirma patrones en M30, H1 y H4
    - M30: Timeframe principal (detección)
    - H1: Confirmación de tendencia
    - H4: Validación de contexto
    """
    
    def __init__(self, symbol="XAUUSD"):
        self.enabled = True
        self.symbol = symbol
        self.min_body_pips = CS_MIN_BODY_PIPS
        self.min_confidence = CS_MIN_CONFIDENCE
        self.min_engulf_ratio = CS_MIN_ENGULF_RATIO
        self.require_trend_context = CS_REQUIRE_TREND_CONTEXT
        self.volume_confirmation = CS_VOLUME_CONFIRMATION
        
        # Cooldown interno
        self.cooldown_minutes = CS_COOLDOWN_AFTER_SIGNAL_MINUTES
        self.min_candles_between = CS_MIN_CANDLES_BETWEEN_SIGNALS
        self.last_signal_time = None
        self.last_signal_candle_count = None
        
        # 🆕 MTF: Configuración de timeframes
        self.mtf_timeframes = {
            'M30': mt5.TIMEFRAME_M30,  # Principal
            'H1': mt5.TIMEFRAME_H1,    # Confirmación
            'H4': mt5.TIMEFRAME_H4     # Contexto
        }
        
        # Cache MTF
        self.mtf_cache = {}
        self.last_mtf_update = {}
        
        # Estadísticas
        self.pattern_stats = {
            'bullish_engulfing': {'detected': 0, 'executed': 0, 'blocked_cooldown': 0},
            'bearish_engulfing': {'detected': 0, 'executed': 0, 'blocked_cooldown': 0}
        }
        
        self.total_blocked_by_cooldown = 0
    
    def is_in_cooldown(self, df):
        """Verifica cooldown"""
        now = datetime.now()
        current_candle_count = len(df)
        
        if self.last_signal_time is not None:
            time_elapsed = (now - self.last_signal_time).total_seconds() / 60
            
            if time_elapsed < self.cooldown_minutes:
                time_remaining = self.cooldown_minutes - time_elapsed
                return True, f"Cooldown: {time_remaining:.1f} min", time_remaining
        
        if self.last_signal_candle_count is not None:
            candles_elapsed = current_candle_count - self.last_signal_candle_count
            
            if candles_elapsed < self.min_candles_between:
                candles_remaining = self.min_candles_between - candles_elapsed
                return True, f"Cooldown: {candles_remaining} velas", 0
        
        return False, "OK", 0
    
    def register_signal_generated(self, df):
        """Registra señal y activa cooldown"""
        self.last_signal_time = datetime.now()
        self.last_signal_candle_count = len(df)
    
    def get_mtf_data(self, timeframe_name, bars=50):
        """Obtiene datos de un timeframe específico con cache"""
        now = datetime.now()
        cache_key = timeframe_name
        
        # Verificar cache
        if cache_key in self.mtf_cache:
            last_update = self.last_mtf_update.get(cache_key)
            if last_update and (now - last_update).total_seconds() < 60:
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
    
    def get_candle_parts(self, candle):
        """Extrae partes de una vela"""
        o = candle['open']
        h = candle['high']
        l = candle['low']
        c = candle['close']
        
        body = abs(c - o)
        total_range = h - l
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        
        is_bullish = c > o
        
        return {
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'body': body,
            'range': total_range,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'is_bullish': is_bullish,
            'body_pips': body / 0.01
        }
    
    def check_trend(self, df, lookback=5):
        """Detecta tendencia"""
        if len(df) < lookback + 50:
            return 'neutral'
        
        # Calcular EMAs si no existen
        if 'ema_21' not in df.columns:
            import ta
            df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
            df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
        
        recent = df.tail(lookback)
        
        ema_21_trend = recent['ema_21'].iloc[-1] > recent['ema_21'].iloc[0]
        ema_50_trend = recent['ema_50'].iloc[-1] > recent['ema_50'].iloc[0]
        
        last = df.iloc[-1]
        
        if last['ema_21'] > last['ema_50'] and ema_21_trend and ema_50_trend:
            return 'uptrend'
        elif last['ema_21'] < last['ema_50'] and not ema_21_trend and not ema_50_trend:
            return 'downtrend'
        
        return 'sideways'
    
    def check_volume_confirmation(self, df):
        """Verifica pico de volumen"""
        if 'tick_volume' not in df.columns or len(df) < 10:
            return False, 1.0
        
        current_volume = df.iloc[-1]['tick_volume']
        avg_volume = df.tail(10)['tick_volume'].mean()
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        has_spike = volume_ratio >= 1.5
        
        return has_spike, volume_ratio
    
    def analyze_mtf_context(self, pattern_type):
        """
        🆕 Analiza contexto multi-timeframe
        
        Args:
            pattern_type: 'bullish' o 'bearish'
        
        Returns:
            dict: Análisis MTF con confianza ajustada
        """
        mtf_analysis = {
            'M30': {'trend': None, 'valid': False},
            'H1': {'trend': None, 'valid': False},
            'H4': {'trend': None, 'valid': False},
            'alignment': False,
            'confidence_boost': 0.0
        }
        
        # Obtener tendencias de cada TF
        for tf_name in ['M30', 'H1', 'H4']:
            df_tf = self.get_mtf_data(tf_name, bars=100)
            
            if df_tf is None or len(df_tf) < 50:
                continue
            
            trend = self.check_trend(df_tf, lookback=10)
            mtf_analysis[tf_name]['trend'] = trend
            
            # Validar si la tendencia apoya el patrón
            if pattern_type == 'bullish':
                mtf_analysis[tf_name]['valid'] = trend in ['downtrend', 'sideways']
            else:  # bearish
                mtf_analysis[tf_name]['valid'] = trend in ['uptrend', 'sideways']
        
        # Calcular alineación
        valid_count = sum(1 for tf in ['M30', 'H1', 'H4'] if mtf_analysis[tf]['valid'])
        
        # Ajustar confianza según alineación
        if valid_count == 3:
            mtf_analysis['alignment'] = True
            mtf_analysis['confidence_boost'] = 0.10  # +10% todas alineadas
        elif valid_count == 2:
            mtf_analysis['alignment'] = True
            mtf_analysis['confidence_boost'] = 0.05  # +5% dos alineadas
        else:
            mtf_analysis['alignment'] = False
            mtf_analysis['confidence_boost'] = 0.0
        
        return mtf_analysis
    
    def is_bullish_engulfing_enhanced(self, df):
        """BULLISH ENGULFING con MTF"""
        if len(df) < 2:
            return False, 0, {}
        
        current = self.get_candle_parts(df.iloc[-1])
        previous = self.get_candle_parts(df.iloc[-2])
        
        # Validación básica
        prev_bearish = not previous['is_bullish']
        curr_bullish = current['is_bullish']
        engulfs = (current['open'] <= previous['close'] and 
                  current['close'] >= previous['open'])
        
        if not (prev_bearish and curr_bullish and engulfs):
            return False, 0, {}
        
        # Ratio de envolvimiento
        engulf_ratio = current['body'] / previous['body'] if previous['body'] > 0 else 0
        
        if engulf_ratio < self.min_engulf_ratio:
            return False, 0, {'reason': f'Ratio bajo: {engulf_ratio:.1f}x'}
        
        # Tamaño mínimo
        if current['body_pips'] < self.min_body_pips:
            return False, 0, {'reason': f'Cuerpo pequeño: {current["body_pips"]:.0f} pips'}
        
        # Tendencia local
        trend = self.check_trend(df)
        
        if self.require_trend_context and trend not in ['downtrend', 'sideways']:
            return False, 0, {'reason': f'Tendencia incorrecta: {trend}'}
        
        # Volumen
        has_volume_spike, volume_ratio = self.check_volume_confirmation(df)
        
        # 🆕 ANÁLISIS MTF
        mtf_analysis = self.analyze_mtf_context('bullish')
        
        # CALCULAR CONFIANZA
        confidence = 0.55  # Base
        
        if trend == 'downtrend':
            confidence += 0.10
        
        if engulf_ratio > 2.0:
            extra_ratio = engulf_ratio - 2.0
            confidence += min(extra_ratio * 0.05, 0.15)
        
        if has_volume_spike:
            confidence += 0.05
        
        # 🆕 BOOST MTF
        confidence += mtf_analysis['confidence_boost']
        
        confidence = min(confidence, 0.85)
        
        details = {
            'engulf_ratio': engulf_ratio,
            'trend_context': trend,
            'volume_ratio': volume_ratio,
            'has_volume_spike': has_volume_spike,
            'body_pips': current['body_pips'],
            'mtf_analysis': mtf_analysis,
            'mtf_aligned': mtf_analysis['alignment']
        }
        
        self.pattern_stats['bullish_engulfing']['detected'] += 1
        
        return True, confidence, details
    
    def is_bearish_engulfing_enhanced(self, df):
        """BEARISH ENGULFING con MTF"""
        if len(df) < 2:
            return False, 0, {}
        
        current = self.get_candle_parts(df.iloc[-1])
        previous = self.get_candle_parts(df.iloc[-2])
        
        # Validación básica
        prev_bullish = previous['is_bullish']
        curr_bearish = not current['is_bullish']
        engulfs = (current['open'] >= previous['close'] and 
                  current['close'] <= previous['open'])
        
        if not (prev_bullish and curr_bearish and engulfs):
            return False, 0, {}
        
        # Ratio
        engulf_ratio = current['body'] / previous['body'] if previous['body'] > 0 else 0
        
        if engulf_ratio < self.min_engulf_ratio:
            return False, 0, {'reason': f'Ratio bajo: {engulf_ratio:.1f}x'}
        
        # Tamaño
        if current['body_pips'] < self.min_body_pips:
            return False, 0, {'reason': f'Cuerpo pequeño: {current["body_pips"]:.0f} pips'}
        
        # Tendencia
        trend = self.check_trend(df)
        
        if self.require_trend_context and trend not in ['uptrend', 'sideways']:
            return False, 0, {'reason': f'Tendencia incorrecta: {trend}'}
        
        # Volumen
        has_volume_spike, volume_ratio = self.check_volume_confirmation(df)
        
        # 🆕 ANÁLISIS MTF
        mtf_analysis = self.analyze_mtf_context('bearish')
        
        # CONFIANZA
        confidence = 0.55
        
        if trend == 'uptrend':
            confidence += 0.10
        
        if engulf_ratio > 2.0:
            extra_ratio = engulf_ratio - 2.0
            confidence += min(extra_ratio * 0.05, 0.15)
        
        if has_volume_spike:
            confidence += 0.05
        
        # 🆕 BOOST MTF
        confidence += mtf_analysis['confidence_boost']
        
        confidence = min(confidence, 0.85)
        
        details = {
            'engulf_ratio': engulf_ratio,
            'trend_context': trend,
            'volume_ratio': volume_ratio,
            'has_volume_spike': has_volume_spike,
            'body_pips': current['body_pips'],
            'mtf_analysis': mtf_analysis,
            'mtf_aligned': mtf_analysis['alignment']
        }
        
        self.pattern_stats['bearish_engulfing']['detected'] += 1
        
        return True, confidence, details
    
    def get_signal(self, df):
        """Genera señal con MTF y cooldown"""
        if not self.enabled or len(df) < 3:
            return None
        
        # Verificar cooldown
        in_cooldown, reason, time_remaining = self.is_in_cooldown(df)
        
        if in_cooldown:
            self.total_blocked_by_cooldown += 1
            return None
        
        # BULLISH ENGULFING
        is_bullish_eng, confidence, details = self.is_bullish_engulfing_enhanced(df)
        
        if is_bullish_eng and confidence >= self.min_confidence:
            self.pattern_stats['bullish_engulfing']['executed'] += 1
            self.register_signal_generated(df)
            
            # Construir razón con info MTF
            reason = f"Candlestick: Bullish Engulfing {details['engulf_ratio']:.1f}x"
            if details.get('has_volume_spike'):
                reason += " + Vol"
            if details.get('mtf_aligned'):
                mtf = details['mtf_analysis']
                aligned_tfs = [tf for tf in ['M30', 'H1', 'H4'] if mtf[tf]['valid']]
                reason += f" + MTF({'+'.join(aligned_tfs)})"
            
            return {
                'signal': 1,
                'confidence': confidence,
                'reason': reason,
                'sl_pips': 40,
                'tp_pips': 100,
                'pattern': 'bullish_engulfing_enhanced',
                'details': details
            }
        
        # BEARISH ENGULFING
        is_bearish_eng, confidence, details = self.is_bearish_engulfing_enhanced(df)
        
        if is_bearish_eng and confidence >= self.min_confidence:
            self.pattern_stats['bearish_engulfing']['executed'] += 1
            self.register_signal_generated(df)
            
            reason = f"Candlestick: Bearish Engulfing {details['engulf_ratio']:.1f}x"
            if details.get('has_volume_spike'):
                reason += " + Vol"
            if details.get('mtf_aligned'):
                mtf = details['mtf_analysis']
                aligned_tfs = [tf for tf in ['M30', 'H1', 'H4'] if mtf[tf]['valid']]
                reason += f" + MTF({'+'.join(aligned_tfs)})"
            
            return {
                'signal': -1,
                'confidence': confidence,
                'reason': reason,
                'sl_pips': 40,
                'tp_pips': 100,
                'pattern': 'bearish_engulfing_enhanced',
                'details': details
            }
        
        return None
    
    def get_statistics(self):
        """Retorna estadísticas"""
        stats = self.pattern_stats.copy()
        stats['total_blocked_by_cooldown'] = self.total_blocked_by_cooldown
        stats['last_signal_time'] = self.last_signal_time.isoformat() if self.last_signal_time else None
        
        return stats
    
    def get_cooldown_status(self):
        """Retorna estado del cooldown"""
        if self.last_signal_time is None:
            return {
                'in_cooldown': False,
                'can_generate_signal': True,
                'message': 'Sin señales previas - Puede operar'
            }
        
        now = datetime.now()
        time_elapsed = (now - self.last_signal_time).total_seconds() / 60
        
        if time_elapsed < self.cooldown_minutes:
            time_remaining = self.cooldown_minutes - time_elapsed
            return {
                'in_cooldown': True,
                'can_generate_signal': False,
                'time_remaining_minutes': time_remaining,
                'message': f'En cooldown: {time_remaining:.1f} min restantes'
            }
        else:
            return {
                'in_cooldown': False,
                'can_generate_signal': True,
                'message': 'Cooldown terminado - Puede operar'
            }
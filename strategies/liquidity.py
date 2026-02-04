"""
╔══════════════════════════════════════════════════════════════════════════╗
║         ESTRATEGIA LIQUIDITY SYSTEM v5.3 BALANCED - SMC BALANCEADA      ║
║                                                                          ║
║  🆕 v5.3 BALANCED: Versión equilibrada entre calidad y frecuencia       ║
║                                                                          ║
║  DIFERENCIAS vs v5.3 STRICT:                                            ║
║  ✅ FVG gap mínimo: 50 → 30 pips (más señales)                          ║
║  ✅ OB impulso mínimo: 800 → 600 pips (más señales)                     ║
║  ✅ OB reacciones: 2 → 1 (menos restrictivo)                            ║
║  ✅ Sweep wick mínimo: 1000 → 700 pips (más señales)                    ║
║  ✅ Opera en TODAS las sesiones (no bloquea Asia para OB/FVG)           ║
║  ✅ Confianza ajustada según sesión (no bloquea señales)                ║
║                                                                          ║
║  📊 EXPECTATIVAS AJUSTADAS:                                             ║
║  • Win Rate esperado: 55-70% (vs 60-80% strict)                         ║
║  • Trades por día: 3-8 (vs 1-3 strict)                                  ║
║  • Risk/Reward: 1.8-2.2 (vs 2.0-2.5 strict)                             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
from datetime import datetime, time
from config import (
    LIQ_LOOKBACK_BARS, LIQ_SWEEP_TOLERANCE_PIPS,
    LIQ_MIN_WICK_SIZE_PIPS, LIQ_MIN_DISTANCE_FROM_SWEEP_PIPS
)


class LiquiditySystem:
    """
    Sistema Balanceado de Liquidez - v5.4 OPTIMIZADO
    
    🔧 CAMBIOS:
    - Cache más inteligente (respeta edad de zonas)
    - Accepta posiciones estratégicas en zonas (no TODO)
    - Confianza más realista según contexto
    - Cooldown interno entre señales
    - Prioriza confluencia (máxima calidad)
    """
    
    def __init__(self):
        self.enabled = True
        
        # Parámetros base
        self.lookback_bars = LIQ_LOOKBACK_BARS
        self.sweep_tolerance_pips = LIQ_SWEEP_TOLERANCE_PIPS
        
        # 🔧 PARÁMETROS OPTIMIZADOS (BALANCED)
        self.min_wick_size_pips = 800  # Aumentado de 700 (más selectivo)
        self.min_distance_from_sweep_pips = 100  # Aumentado de 80
        
        # FVG más restrictivo
        self.fvg_min_gap_pips = 40  # Aumentado de 30
        self.fvg_max_age_bars = 20  # Reducido de 25
        
        # Order Blocks más selectivo
        self.ob_min_impulse_pips = 700  # Aumentado de 600
        self.ob_min_reaction_touches = 2  # Aumentado de 1 (necesita confirmación)
        
        # 🔧 NUEVO: Cooldown interno
        self.last_signal_time = None
        self.min_signal_interval_minutes = 15  # Mínimo 15 min entre señales
        
        self.cached_order_blocks = []
        self.cached_fvgs = []
        self.last_ob_calculation = None
        self.last_fvg_calculation = None
        
        self.session_stats = {
            'london_ny_overlap': {'signals': 0, 'executed': 0},
            'london_only': {'signals': 0, 'executed': 0},
            'ny_only': {'signals': 0, 'executed': 0},
            'asian': {'signals': 0, 'executed': 0}
        }
    
    def get_trading_session(self):
        """
        Identifica sesión actual (solo para ajustar confianza, no bloquear)
        """
        now_utc = datetime.utcnow()
        current_time = now_utc.time()
        
        london_ny_start = time(13, 0)
        london_ny_end = time(17, 0)
        london_start = time(8, 0)
        london_end = time(17, 0)
        ny_start = time(13, 0)
        ny_end = time(22, 0)
        asian_start = time(0, 0)
        asian_end = time(9, 0)
        
        if london_ny_start <= current_time <= london_ny_end:
            return 'london_ny_overlap', 1.0
        elif london_start <= current_time <= london_end:
            return 'london_only', 0.9  # Aumentado de 0.8
        elif ny_start <= current_time <= ny_end:
            return 'ny_only', 0.9  # Aumentado de 0.8
        elif asian_start <= current_time <= asian_end:
            return 'asian', 0.6  # Aumentado de 0.3 (más permisivo)
        else:
            return 'off_hours', 0.5  # Aumentado de 0.1
    
    def detect_fair_value_gap(self, df):
        """
        🆕 BALANCEADO: FVG con gap mínimo de 30 pips
        """
        if len(df) < 10:
            return []
        
        fvgs = []
        recent = df.tail(self.fvg_max_age_bars + 3).copy()
        
        for i in range(2, len(recent)):
            candle_1 = recent.iloc[i-2]
            candle_2 = recent.iloc[i-1]
            candle_3 = recent.iloc[i]
            
            # BULLISH FVG
            if candle_3['low'] > candle_1['high']:
                gap_size_pips = (candle_3['low'] - candle_1['high']) / 0.01
                
                # 🆕 Gap mínimo reducido a 30 pips
                if gap_size_pips >= self.fvg_min_gap_pips:
                    impulse_pips = (candle_2['close'] - candle_2['open']) / 0.01
                    
                    # 🆕 Impulso mínimo reducido a 20 pips
                    if impulse_pips > 20:
                        fvgs.append({
                            'type': 'bullish_fvg',
                            'gap_high': float(candle_3['low']),
                            'gap_low': float(candle_1['high']),
                            'gap_mid': float((candle_3['low'] + candle_1['high']) / 2),
                            'gap_size_pips': gap_size_pips,
                            'impulse_pips': impulse_pips,
                            'formation_index': i,
                            'time': candle_3['time'],
                            'filled': False
                        })
            
            # BEARISH FVG
            elif candle_3['high'] < candle_1['low']:
                gap_size_pips = (candle_1['low'] - candle_3['high']) / 0.01
                
                if gap_size_pips >= self.fvg_min_gap_pips:
                    impulse_pips = abs((candle_2['close'] - candle_2['open']) / 0.01)
                    
                    if impulse_pips > 20:
                        fvgs.append({
                            'type': 'bearish_fvg',
                            'gap_high': float(candle_1['low']),
                            'gap_low': float(candle_3['high']),
                            'gap_mid': float((candle_1['low'] + candle_3['high']) / 2),
                            'gap_size_pips': gap_size_pips,
                            'impulse_pips': impulse_pips,
                            'formation_index': i,
                            'time': candle_3['time'],
                            'filled': False
                        })
        
        return fvgs
    
    def check_fvg_interaction(self, fvgs, current_price):
        """
        🆕 BALANCEADO: Acepta todo el rango del gap (no solo 50%)
        """
        for fvg in fvgs:
            if fvg['filled']:
                continue
            
            gap_range = fvg['gap_high'] - fvg['gap_low']
            
            # 🆕 Acepta TODO el gap (antes solo 50%)
            if fvg['gap_low'] <= current_price <= fvg['gap_high']:
                position_in_gap = (current_price - fvg['gap_low']) / gap_range if gap_range > 0 else 0.5
                
                if fvg['type'] == 'bullish_fvg':
                    # 🆕 Acepta todo el gap (antes < 0.5)
                    confidence = 0.65 + (fvg['gap_size_pips'] / 1000) * 0.08
                    confidence = min(confidence, 0.80)
                    
                    return {
                        'signal': 1,
                        'confidence': confidence,
                        'fvg': fvg,
                        'position_in_gap': position_in_gap
                    }
                
                elif fvg['type'] == 'bearish_fvg':
                    # 🆕 Acepta todo el gap (antes > 0.5)
                    confidence = 0.65 + (fvg['gap_size_pips'] / 1000) * 0.08
                    confidence = min(confidence, 0.80)
                    
                    return {
                        'signal': -1,
                        'confidence': confidence,
                        'fvg': fvg,
                        'position_in_gap': position_in_gap
                    }
        
        return None
    
    def detect_liquidity_sweep_enhanced(self, df, current_price):
        """
        🆕 BALANCEADO: Sweep con mecha mínima de 700 pips
        """
        if len(df) < self.lookback_bars:
            return None
        
        recent = df.tail(self.lookback_bars).copy()
        
        recent_high = recent['high'].max()
        recent_low = recent['low'].min()
        
        current_candle = df.iloc[-1]
        
        candle_open = current_candle['open']
        candle_close = current_candle['close']
        candle_high = current_candle['high']
        candle_low = current_candle['low']
        
        session, session_priority = self.get_trading_session()
        
        # BULLISH SWEEP
        if candle_low <= recent_low + (self.sweep_tolerance_pips * 0.1):
            
            lower_wick_size_pips = (min(candle_open, candle_close) - candle_low) / 0.1
            
            # 🆕 Mecha mínima reducida a 700 pips
            if lower_wick_size_pips >= self.min_wick_size_pips:
                
                distance_from_sweep = (current_price - candle_low) / 0.1
                
                # 🆕 Distancia mínima reducida a 80 pips
                if distance_from_sweep >= self.min_distance_from_sweep_pips:
                    
                    base_confidence = 0.68 + (lower_wick_size_pips - 700) * 0.00008
                    base_confidence = min(base_confidence, 0.82)
                    
                    # 🆕 Ajuste de sesión menos agresivo
                    session_confidence = base_confidence * (0.85 + session_priority * 0.15)
                    
                    return {
                        'type': 'bullish_sweep',
                        'swept_level': candle_low,
                        'wick_size': lower_wick_size_pips,
                        'distance_from_sweep': distance_from_sweep,
                        'confidence': session_confidence,
                        'current_price': current_price,
                        'session': session,
                        'session_priority': session_priority
                    }
        
        # BEARISH SWEEP
        if candle_high >= recent_high - (self.sweep_tolerance_pips * 0.01):
            
            upper_wick_size_pips = (candle_high - max(candle_open, candle_close)) / 0.01
            
            if upper_wick_size_pips >= self.min_wick_size_pips:
                
                distance_from_sweep = (candle_high - current_price) / 0.01
                
                if distance_from_sweep >= self.min_distance_from_sweep_pips:
                    
                    base_confidence = 0.68 + (upper_wick_size_pips - 700) * 0.00008
                    base_confidence = min(base_confidence, 0.82)
                    
                    session_confidence = base_confidence * (0.85 + session_priority * 0.15)
                    
                    return {
                        'type': 'bearish_sweep',
                        'swept_level': candle_high,
                        'wick_size': upper_wick_size_pips,
                        'distance_from_sweep': distance_from_sweep,
                        'confidence': session_confidence,
                        'current_price': current_price,
                        'session': session,
                        'session_priority': session_priority
                    }
        
        return None
    
    def find_order_blocks_enhanced(self, df):
        """
        🆕 BALANCEADO: OB con impulso mínimo de 600 pips y solo 1 reacción
        """
        if len(df) < 50:
            return []
        
        recent = df.tail(50).copy()
        order_blocks = []
        
        for i in range(5, len(recent) - 5):
            current = recent.iloc[i]
            next_candles = recent.iloc[i+1:i+4]
            
            # BULLISH ORDER BLOCK
            if current['close'] < current['open']:
                bullish_impulse = sum(1 for idx in range(len(next_candles)) 
                                     if next_candles.iloc[idx]['close'] > next_candles.iloc[idx]['open'])
                
                total_move = next_candles.iloc[-1]['close'] - current['low']
                move_pips = total_move / 0.01
                
                # 🆕 Impulso mínimo reducido a 600 pips
                if bullish_impulse >= 2 and move_pips > self.ob_min_impulse_pips:
                    
                    ob_zone_high = current['high']
                    ob_zone_low = current['low']
                    
                    future_candles = recent.iloc[i+4:]
                    reaction_count = 0
                    
                    for future_idx in range(len(future_candles)):
                        future = future_candles.iloc[future_idx]
                        if ob_zone_low <= future['low'] <= ob_zone_high:
                            reaction_count += 1
                    
                    # 🆕 Solo requiere 1 reacción (antes 2)
                    if reaction_count >= self.ob_min_reaction_touches:
                        order_blocks.append({
                            'type': 'bullish_ob',
                            'zone_high': float(ob_zone_high),
                            'zone_low': float(ob_zone_low),
                            'zone_mid': float((ob_zone_high + ob_zone_low) / 2),
                            'strength': move_pips,
                            'reaction_count': reaction_count,
                            'formation_index': i,
                            'time': current['time'],
                            'age_bars': len(recent) - i
                        })
            
            # BEARISH ORDER BLOCK
            elif current['close'] > current['open']:
                bearish_impulse = sum(1 for idx in range(len(next_candles)) 
                                     if next_candles.iloc[idx]['close'] < next_candles.iloc[idx]['open'])
                
                total_move = current['high'] - next_candles.iloc[-1]['close']
                move_pips = total_move / 0.01
                
                if bearish_impulse >= 2 and move_pips > self.ob_min_impulse_pips:
                    
                    ob_zone_high = current['high']
                    ob_zone_low = current['low']
                    
                    future_candles = recent.iloc[i+4:]
                    reaction_count = 0
                    
                    for future_idx in range(len(future_candles)):
                        future = future_candles.iloc[future_idx]
                        if ob_zone_low <= future['high'] <= ob_zone_high:
                            reaction_count += 1
                    
                    if reaction_count >= self.ob_min_reaction_touches:
                        order_blocks.append({
                            'type': 'bearish_ob',
                            'zone_high': float(ob_zone_high),
                            'zone_low': float(ob_zone_low),
                            'zone_mid': float((ob_zone_high + ob_zone_low) / 2),
                            'strength': move_pips,
                            'reaction_count': reaction_count,
                            'formation_index': i,
                            'time': current['time'],
                            'age_bars': len(recent) - i
                        })
        
        order_blocks.sort(key=lambda x: (x['reaction_count'], x['strength'], -x['age_bars']), reverse=True)
        
        return order_blocks[:8]  # 🆕 Aumentado de 5 a 8
    
    def check_order_block_touch_enhanced(self, order_blocks, current_price):
        """
        🆕 BALANCEADO: Acepta todo el rango del OB
        """
        for ob in order_blocks:
            zone_range = ob['zone_high'] - ob['zone_low']
            
            # 🆕 Acepta TODO el rango del OB
            if ob['zone_low'] <= current_price <= ob['zone_high']:
                position = (current_price - ob['zone_low']) / zone_range if zone_range > 0 else 0.5
                
                if ob['type'] == 'bullish_ob':
                    # 🆕 Todo el OB es válido (antes < 0.6)
                    base_confidence = 0.62
                    
                    strength_bonus = min((ob['strength'] / 2000) * 0.08, 0.08)
                    reaction_bonus = min((ob['reaction_count'] / 5) * 0.06, 0.06)
                    age_bonus = max(0, (20 - ob['age_bars']) / 20 * 0.04)
                    
                    confidence = base_confidence + strength_bonus + reaction_bonus + age_bonus
                    confidence = min(confidence, 0.82)
                    
                    return {
                        'signal': 1,
                        'confidence': confidence,
                        'ob': ob,
                        'position_in_zone': position
                    }
                
                elif ob['type'] == 'bearish_ob':
                    # 🆕 Todo el OB es válido (antes > 0.4)
                    base_confidence = 0.62
                    strength_bonus = min((ob['strength'] / 2000) * 0.08, 0.08)
                    reaction_bonus = min((ob['reaction_count'] / 5) * 0.06, 0.06)
                    age_bonus = max(0, (20 - ob['age_bars']) / 20 * 0.04)
                    
                    confidence = base_confidence + strength_bonus + reaction_bonus + age_bonus
                    confidence = min(confidence, 0.82)
                    
                    return {
                        'signal': -1,
                        'confidence': confidence,
                        'ob': ob,
                        'position_in_zone': position
                    }
        
        return None
    
    def calculate_confluence_score(self, signal_data, fvg_signal, ob_signal, sweep_data):
        """
        Sistema de Confluence Scoring
        """
        confluence_factors = []
        base_confidence = signal_data['confidence']
        
        if fvg_signal:
            confluence_factors.append('FVG')
            base_confidence += 0.04  # Reducido de 0.05
        
        if ob_signal:
            confluence_factors.append('OB')
            base_confidence += 0.04  # Reducido de 0.05
        
        if sweep_data:
            confluence_factors.append('SWEEP')
            base_confidence += 0.03
        
        session, session_priority = self.get_trading_session()
        if session == 'london_ny_overlap':
            confluence_factors.append('LONDON_NY')
            base_confidence += 0.05  # Reducido de 0.07
        elif session in ['london_only', 'ny_only']:
            confluence_factors.append(session.upper())
            base_confidence += 0.02  # Reducido de 0.03
        
        final_confidence = min(base_confidence, 0.88)  # Reducido de 0.92
        
        return {
            'confluence_factors': confluence_factors,
            'confluence_count': len(confluence_factors),
            'final_confidence': final_confidence,
            'session': session
        }
    
    def get_signal(self, df, current_price):
        """
        🔧 v5.4: Genera señales SELECTIVAS y BALANCEADAS
        
        PRIORIDAD:
        1. Máxima confluencia (mejor relación riesgo/recompensa)
        2. Sweep + OB confirmado
        3. FVG + OB confluencia
        4. FVG solo (solo si es grande y reciente)
        """
        if not self.enabled or len(df) < 50:
            return None
        
        # 🔧 NUEVO: Cooldown interno (máximo 1 señal cada 15 min)
        if self.last_signal_time:
            minutes_since_last = (datetime.now() - self.last_signal_time).total_seconds() / 60
            if minutes_since_last < self.min_signal_interval_minutes:
                return None  # Esperar mínimo intervalo
        
        session, session_priority = self.get_trading_session()
        
        # 1. DETECTAR FAIR VALUE GAPS (cache más inteligente)
        now = datetime.now()
        if (self.last_fvg_calculation is None or 
            (now - self.last_fvg_calculation).total_seconds() > 120):  # Cada 2 min
            self.cached_fvgs = self.detect_fair_value_gap(df)
            self.last_fvg_calculation = now
        
        fvg_signal = self.check_fvg_interaction(self.cached_fvgs, current_price)
        
        # 2. DETECTAR ORDER BLOCKS (cache más inteligente)
        if (self.last_ob_calculation is None or 
            (now - self.last_ob_calculation).total_seconds() > 120):  # Cada 2 min
            self.cached_order_blocks = self.find_order_blocks_enhanced(df)
            self.last_ob_calculation = now
        
        ob_signal = self.check_order_block_touch_enhanced(self.cached_order_blocks, current_price)
        
        # 3. DETECTAR LIQUIDITY SWEEPS
        sweep = self.detect_liquidity_sweep_enhanced(df, current_price)
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDAD 1: MÁXIMA CONFLUENCIA (FVG + OB + Sweep)
        # ═══════════════════════════════════════════════════════════
        if fvg_signal and ob_signal and sweep:
            if fvg_signal['signal'] == ob_signal['signal'] == (1 if sweep['type'] == 'bullish_sweep' else -1):
                signal_data = fvg_signal.copy()
                confluence = self.calculate_confluence_score(signal_data, fvg_signal, ob_signal, sweep)
                
                # 🔧 MEJORA: Confianza más realista
                final_confidence = min(0.78, confluence['final_confidence'])  # Cap en 78%
                
                direction = "BUY" if signal_data['signal'] == 1 else "SELL"
                
                self.last_signal_time = now
                
                return {
                    'signal': signal_data['signal'],
                    'confidence': final_confidence,
                    'reason': f"Liquidez: ⭐ CONFLUENCIA MÁXIMA {direction} - FVG+OB+Sweep",
                    'sl_pips': 45,
                    'tp_pips': 130,
                    'liquidity_type': 'max_confluence',
                    'confluence_factors': confluence['confluence_factors'],
                    'confluence_count': 3,
                    'session': confluence['session']
                }
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDAD 2: SWEEP + ORDER BLOCK (muy confiable)
        # ═══════════════════════════════════════════════════════════
        if sweep and ob_signal:
            sweep_signal = 1 if sweep['type'] == 'bullish_sweep' else -1
            
            if sweep_signal == ob_signal['signal']:
                signal_data = ob_signal.copy()
                confluence = self.calculate_confluence_score(signal_data, None, ob_signal, sweep)
                
                # 🔧 MEJORA: Confianza más conservadora
                final_confidence = min(0.75, confluence['final_confidence'])
                
                direction = "BUY" if signal_data['signal'] == 1 else "SELL"
                
                self.last_signal_time = now
                
                return {
                    'signal': signal_data['signal'],
                    'confidence': final_confidence,
                    'reason': f"Liquidez: ✅ Sweep+OB {direction} - Mecha {sweep['wick_size']:.0f}p",
                    'sl_pips': 50,
                    'tp_pips': 120,
                    'liquidity_type': 'sweep_ob',
                    'confluence_factors': confluence['confluence_factors'],
                    'confluence_count': 2,
                    'session': confluence['session']
                }
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDAD 3: FVG + ORDER BLOCK (confluencia media)
        # ═══════════════════════════════════════════════════════════
        if fvg_signal and ob_signal:
            if fvg_signal['signal'] == ob_signal['signal']:
                signal_data = fvg_signal.copy()
                confluence = self.calculate_confluence_score(signal_data, fvg_signal, ob_signal, None)
                
                final_confidence = min(0.72, confluence['final_confidence'])
                direction = "BUY" if signal_data['signal'] == 1 else "SELL"
                fvg = fvg_signal['fvg']
                ob = ob_signal['ob']
                
                self.last_signal_time = now
                
                return {
                    'signal': signal_data['signal'],
                    'confidence': final_confidence,
                    'reason': f"Liquidez: FVG+OB {direction} @ {confluence['session'].upper()}",
                    'sl_pips': 50,
                    'tp_pips': 125,
                    'liquidity_type': 'high_confluence',
                    'confluence_factors': confluence['confluence_factors'],
                    'confluence_count': 2,
                    'session': confluence['session'],
                    'fvg_size': fvg['gap_size_pips'],
                    'ob_strength': ob['strength']
                }
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDAD 4: FVG SOLO (muy selectivo)
        # ═══════════════════════════════════════════════════════════
        if fvg_signal:
            fvg = fvg_signal['fvg']
            
            # 🔧 MEJORA: Solo si es RECIENTE y GRANDE
            # Calcular edad del FVG basado en su índice de formación
            if self.cached_fvgs:
                current_index = len(df) - 1
                formation_index = fvg.get('formation_index', 0)
                age = current_index - formation_index
            else:
                age = 50  # Default si no hay FVGs cacheados
            
            # Solo FVG de hace menos de 15 velas y gap > 50 pips
            if age < 15 and fvg['gap_size_pips'] > 50:
                
                direction = "BUY" if fvg_signal['signal'] == 1 else "SELL"
                final_confidence = min(0.68, 0.65 + (fvg['gap_size_pips'] / 1000) * 0.08)
                
                self.last_signal_time = now
                
                return {
                    'signal': fvg_signal['signal'],
                    'confidence': final_confidence,
                    'reason': f"Liquidez: FVG {direction} - Gap {fvg['gap_size_pips']:.0f}p (RECIENTE)",
                    'sl_pips': 55,
                    'tp_pips': 120,
                    'liquidity_type': 'fvg_only',
                    'confluence_factors': ['gap_size', 'recency'],
                    'confluence_count': 1,
                    'session': session,
                    'fvg_size': fvg['gap_size_pips']
                }
        
        # ═══════════════════════════════════════════════════════════
        # PRIORIDAD 5: ORDER BLOCK SOLO (menos confiable, muy selectivo)
        # ═══════════════════════════════════════════════════════════
        if ob_signal:
            ob = ob_signal['ob']
            
            # 🔧 MEJORA: Solo si hay MÚLTIPLES reacciones
            if ob['reaction_count'] >= 2:
                
                final_confidence = min(0.70, ob_signal['confidence'])
                direction = "BUY" if ob_signal['signal'] == 1 else "SELL"
                
                self.last_signal_time = now
                
                return {
                    'signal': ob_signal['signal'],
                    'confidence': final_confidence,
                    'reason': f"Liquidez: OB {direction} - {ob['reaction_count']} reacciones",
                    'sl_pips': 55,
                    'tp_pips': 115,
                    'liquidity_type': 'ob_only',
                    'confluence_factors': ['order_block', 'reactions'],
                    'confluence_count': 1,
                    'session': session,
                    'ob_strength': ob['strength']
                }
        
        return None
    
    def get_stats(self):
        """Retorna estadísticas del sistema"""
        total_signals = sum(s['signals'] for s in self.session_stats.values())
        total_executed = sum(s['executed'] for s in self.session_stats.values())
        
        return {
            'total_signals': total_signals,
            'total_executed': total_executed,
            'execution_rate': (total_executed / total_signals * 100) if total_signals > 0 else 0,
            'session_breakdown': self.session_stats,
            'cached_fvgs': len(self.cached_fvgs),
            'cached_order_blocks': len(self.cached_order_blocks)
        }
"""
╔══════════════════════════════════════════════════════════════════════════╗
║              CALCULADORA DINÁMICA DE SL/TP v1.0                          ║
║                                                                          ║
║  Sistema inteligente que calcula SL/TP óptimo según:                    ║
║  - Estrategia que generó la señal                                       ║
║  - Volatilidad actual (ATR)                                             ║
║  - Contexto del mercado (trending, ranging, etc.)                       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from config import STRATEGY_RISK_PROFILES, USE_DYNAMIC_SLTP


class SLTPCalculator:
    """
    Calcula SL/TP dinámico según estrategia y condiciones de mercado
    """
    
    def __init__(self, symbol="XAUUSD", logger=None):
        self.symbol = symbol
        self.logger = logger
        self.profiles = STRATEGY_RISK_PROFILES
        self.point = 0.01  # Para XAUUSD
    
    def send_log(self, message):
        """Envía log si hay logger disponible"""
        if self.logger:
            self.logger.info(message)
    
    def calculate_sltp(self, strategy, signal_data, market_state, df=None):
        """
        Calcula SL/TP óptimo para una señal
        
        Args:
            strategy: Nombre de la estrategia ('ml', 'sr', 'fibo', etc.)
            signal_data: Diccionario con datos de la señal
            market_state: Estado actual del mercado (ATR, tendencia, etc.)
            df: DataFrame con datos de mercado (necesario para algunos cálculos)
        
        Returns:
            dict: {'sl_pips': int, 'tp_pips': int, 'method': str, 'risk_reward': float}
        """
        if not USE_DYNAMIC_SLTP:
            # Modo legacy - usar valores por defecto
            return {
                'sl_pips': signal_data.get('sl_pips', 70),
                'tp_pips': signal_data.get('tp_pips', 140),
                'method': 'legacy_fixed',
                'risk_reward': 2.0
            }
        
        profile = self.profiles.get(strategy)
        
        if not profile:
            self.send_log(f"⚠️ No hay perfil para {strategy}, usando defaults")
            return {
                'sl_pips': 70,
                'tp_pips': 140,
                'method': 'default_fallback',
                'risk_reward': 2.0
            }
        
        sl_type = profile['sl_type']
        
        # Delegar según tipo de SL
        if sl_type == 'fixed':
            return self._calculate_fixed(profile, strategy)
        
        elif sl_type == 'atr_based':
            return self._calculate_atr_based(profile, market_state, strategy)
        
        elif sl_type == 'pattern_based':
            return self._calculate_pattern_based(profile, signal_data, df, strategy)
        
        elif sl_type == 'tight':
            return self._calculate_tight(profile, signal_data, strategy)
        
        elif sl_type == 'zone_based':
            return self._calculate_zone_based(profile, signal_data, strategy)
        
        elif sl_type == 'dynamic':
            return self._calculate_dynamic_sr(profile, signal_data, df, strategy)
        
        else:
            # Fallback
            return {
                'sl_pips': profile.get('sl_pips', 70),
                'tp_pips': profile.get('tp_pips', 140),
                'method': 'profile_default',
                'risk_reward': profile.get('risk_reward', 2.0)
            }
    
    def _calculate_fixed(self, profile, strategy):
        """SL/TP fijo simple"""
        return {
            'sl_pips': profile['sl_pips'],
            'tp_pips': profile['tp_pips'],
            'method': 'fixed',
            'risk_reward': profile['risk_reward']
        }
    
    def _calculate_atr_based(self, profile, market_state, strategy):
        """SL/TP basado en ATR (volatilidad)"""
        atr = market_state.get('atr', 2.0)  # ATR en precio
        
        # Convertir ATR a pips
        atr_pips = atr / self.point
        
        # Calcular SL y TP
        sl_pips = int(atr_pips * profile.get('sl_atr_multiplier', 1.5))
        tp_pips = int(atr_pips * profile.get('tp_atr_multiplier', 3.5))
        
        # Aplicar límites
        min_sl = profile.get('min_sl_pips', 30)
        max_sl = profile.get('max_sl_pips', 100)
        
        sl_pips = max(min_sl, min(sl_pips, max_sl))
        
        # TP proporcional al SL
        tp_pips = int(sl_pips * profile.get('risk_reward', 2.3))
        
        self.send_log(f"📊 {strategy.upper()} ATR: SL={sl_pips}p TP={tp_pips}p (ATR={atr:.2f})")
        
        return {
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'method': 'atr_based',
            'risk_reward': tp_pips / sl_pips if sl_pips > 0 else 2.0,
            'atr_value': atr
        }
    
    def _calculate_pattern_based(self, profile, signal_data, df, strategy):
        """SL/TP basado en tamaño del patrón (para Price Action)"""
        # Obtener detalles del patrón si existen
        details = signal_data.get('details', {})
        
        # Intentar obtener tamaño de la vela del patrón
        if df is not None and len(df) >= 1:
            last_candle = df.iloc[-1]
            candle_body_pips = abs(last_candle['close'] - last_candle['open']) / self.point
            candle_range_pips = (last_candle['high'] - last_candle['low']) / self.point
            
            # Usar el mayor (body o range total)
            pattern_size_pips = max(candle_body_pips, candle_range_pips)
        else:
            # Fallback si no hay df
            pattern_size_pips = 40  # Default razonable
        
        # Calcular SL y TP según multiplicadores
        sl_pips = int(pattern_size_pips * profile.get('sl_multiplier', 1.2))
        tp_pips = int(pattern_size_pips * profile.get('tp_multiplier', 3.0))
        
        # Aplicar límites
        min_sl = profile.get('min_sl_pips', 25)
        max_sl = profile.get('max_sl_pips', 70)
        
        sl_pips = max(min_sl, min(sl_pips, max_sl))
        tp_pips = int(sl_pips * profile.get('risk_reward', 2.5))
        
        self.send_log(f"🕯️ {strategy.upper()} Pattern: SL={sl_pips}p TP={tp_pips}p (Pattern={pattern_size_pips:.0f}p)")
        
        return {
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'method': 'pattern_based',
            'risk_reward': tp_pips / sl_pips if sl_pips > 0 else 2.5,
            'pattern_size_pips': pattern_size_pips
        }
    
    def _calculate_tight(self, profile, signal_data, strategy):
        """SL/TP tight para Candlestick (reversiones rápidas)"""
        base_sl = profile['sl_pips']
        base_tp = profile['tp_pips']
        
        # Si el patrón tiene información de tamaño, ajustar
        if profile.get('use_pattern_size', False):
            details = signal_data.get('details', {})
            body_pips = details.get('body_pips', 0)
            
            if body_pips > 0:
                # Ajustar SL según tamaño del engulfing
                # Engulfing grande = SL más amplio (pero sigue siendo tight)
                if body_pips > 20:
                    sl_pips = int(base_sl * 1.2)  # +20%
                elif body_pips < 12:
                    sl_pips = int(base_sl * 0.8)  # -20%
                else:
                    sl_pips = base_sl
            else:
                sl_pips = base_sl
        else:
            sl_pips = base_sl
        
        tp_pips = int(sl_pips * profile.get('risk_reward', 2.5))
        
        self.send_log(f"🎯 {strategy.upper()} Tight: SL={sl_pips}p TP={tp_pips}p")
        
        return {
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'method': 'tight',
            'risk_reward': tp_pips / sl_pips if sl_pips > 0 else 2.5
        }
    
    def _calculate_zone_based(self, profile, signal_data, strategy):
        """SL/TP basado en zonas de liquidez"""
        base_sl = profile['sl_pips']
        base_tp = profile['tp_pips']
        
        # Si hay información de la zona, ajustar
        zone_size_pips = 0
        
        # Intentar obtener tamaño de FVG si existe
        fvg = signal_data.get('fvg')
        if fvg:
            zone_size_pips = fvg.get('gap_size_pips', 0)
        
        # Intentar obtener tamaño de Order Block si existe
        ob = signal_data.get('ob')
        if ob and zone_size_pips == 0:
            zone_high = ob.get('zone_high', 0)
            zone_low = ob.get('zone_low', 0)
            if zone_high > 0 and zone_low > 0:
                zone_size_pips = (zone_high - zone_low) / self.point
        
        # Calcular SL considerando zona + buffer
        if zone_size_pips > 0:
            buffer_pips = profile.get('zone_buffer_pips', 10)
            sl_pips = int(zone_size_pips + buffer_pips)
            
            # Limitar para evitar SL excesivo
            sl_pips = max(base_sl, min(sl_pips, 100))
        else:
            sl_pips = base_sl
        
        tp_pips = int(sl_pips * profile.get('risk_reward', 2.5))
        
        self.send_log(f"💧 {strategy.upper()} Zone: SL={sl_pips}p TP={tp_pips}p (Zone={zone_size_pips:.0f}p)")
        
        return {
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'method': 'zone_based',
            'risk_reward': tp_pips / sl_pips if sl_pips > 0 else 2.5,
            'zone_size_pips': zone_size_pips
        }
    
    def _calculate_dynamic_sr(self, profile, signal_data, df, strategy):
        """
        SL/TP dinámico para Support/Resistance
        
        Calcula SL hasta el nivel anterior y TP hasta el siguiente nivel
        """
        base_sl = profile['sl_pips']
        base_tp = profile['tp_pips']
        
        # Intentar obtener información de niveles S/R
        level_strength = signal_data.get('level_strength', 0)
        
        # Si no hay información de niveles cercanos, usar base
        if level_strength == 0 or df is None:
            return {
                'sl_pips': base_sl,
                'tp_pips': base_tp,
                'method': 'dynamic_sr_fallback',
                'risk_reward': profile.get('risk_reward', 2.5)
            }
        
        # Ajustar SL según fuerza del nivel
        # Nivel fuerte (más toques) = SL más confiado (más cercano)
        if level_strength >= 4:
            sl_pips = int(base_sl * 0.8)  # -20% SL (más confiado)
        elif level_strength >= 3:
            sl_pips = base_sl  # Mantener base
        else:
            sl_pips = int(base_sl * 1.2)  # +20% SL (menos confiado)
        
        # Aplicar límite máximo
        max_sl = profile.get('max_sl_pips', 80)
        sl_pips = min(sl_pips, max_sl)
        
        # TP proporcional
        tp_pips = int(sl_pips * profile.get('risk_reward', 2.5))
        
        self.send_log(f"📊 {strategy.upper()} S/R Dynamic: SL={sl_pips}p TP={tp_pips}p (Strength={level_strength})")
        
        return {
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'method': 'dynamic_sr',
            'risk_reward': tp_pips / sl_pips if sl_pips > 0 else 2.5,
            'level_strength': level_strength
        }
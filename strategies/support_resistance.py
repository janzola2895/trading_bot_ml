"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   ESTRATEGIA SUPPORT/RESISTANCE v5.2                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from config import SR_LOOKBACK_BARS, SR_MIN_TOUCHES, SR_TOLERANCE_PIPS


class SupportResistanceSystem:
    """Sistema de Trading basado en Soporte y Resistencia - MEJORADO"""
    
    def __init__(self, lookback_bars=SR_LOOKBACK_BARS, 
                 min_touches=SR_MIN_TOUCHES, 
                 tolerance_pips=SR_TOLERANCE_PIPS):
        self.lookback_bars = lookback_bars
        self.min_touches = max(2, min_touches)  # Mínimo 2 toques
        self.tolerance_pips = tolerance_pips
        self.enabled = True
        
        self.cached_levels = []
        self.last_calculation = None
        self.last_signal_level = None  # Evitar señales repetidas
        self.last_signal_time = None
    
    def get_signal(self, df, current_price):
        """
        Genera señal cuando el precio está CERCA de un nivel S/R fuerte
        
        🔧 MEJORADO: Más permisivo pero con validaciones inteligentes
        """
        if not self.enabled or len(df) < 20:
            return None
        
        # ✅ MEJORA 1: Recalcular más frecuentemente (cada 60 segundos)
        now = datetime.now()
        if (self.last_calculation is None or 
            (now - self.last_calculation).total_seconds() > 60):
            levels = self._detect_support_resistance(df)
            self.cached_levels = levels
            self.last_calculation = now
        else:
            levels = self.cached_levels
        
        if not levels or len(levels) == 0:
            return None
        
        # ✅ MEJORA 2: Búsqueda de proximidad (no exactitud)
        signal = self._check_price_proximity(levels, current_price, df)
        
        return signal
    
    def _detect_support_resistance(self, df):
        """
        ✅ MEJORADO: Detección más amplia pero más inteligente
        """
        recent = df.tail(self.lookback_bars).copy()
        highs = recent['high'].values
        lows = recent['low'].values
        closes = recent['close'].values
        
        levels = []
        
        # 🔧 DETECCIÓN DE RESISTANCE (máximos)
        for i in range(2, len(highs) - 2):
            # ✅ MEJORA: Criterio más suave (extremo local, no obligatorio)
            is_local_max = (highs[i] >= highs[i-1] and 
                           highs[i] >= highs[i+1] and
                           highs[i] > closes[i])
            
            if not is_local_max:
                continue
            
            # Contar toques (más flexible)
            touches = 0
            for j in range(len(highs)):
                distance_pips = abs(highs[j] - highs[i]) / 0.01
                
                # ✅ MEJORA: Tolerancia más suave
                if distance_pips <= self.tolerance_pips * 1.5:  # +50% tolerancia
                    touches += 1
            
            # ✅ MEJORA: Aceptar niveles con 2+ toques (no obligatorio 3+)
            if touches >= max(2, self.min_touches - 1):
                levels.append({
                    'level': highs[i],
                    'type': 'resistance',
                    'touches': touches,
                    'strength': touches,
                    'index': i
                })
        
        # 🔧 DETECCIÓN DE SUPPORT (mínimos)
        for i in range(2, len(lows) - 2):
            is_local_min = (lows[i] <= lows[i-1] and 
                           lows[i] <= lows[i+1] and
                           lows[i] < closes[i])
            
            if not is_local_min:
                continue
            
            touches = 0
            for j in range(len(lows)):
                distance_pips = abs(lows[j] - lows[i]) / 0.01
                
                if distance_pips <= self.tolerance_pips * 1.5:
                    touches += 1
            
            if touches >= max(2, self.min_touches - 1):
                levels.append({
                    'level': lows[i],
                    'type': 'support',
                    'touches': touches,
                    'strength': touches,
                    'index': i
                })
        
        # ✅ MEJORA: Ordenar por recencia y fuerza
        levels = sorted(levels, key=lambda x: (-x['index'], -x['strength']))
        
        return levels[:10]  # Top 10 niveles
    
    def _check_price_proximity(self, levels, current_price, df):
        """
        ✅ MEJORA: Revisa si el precio ESTÁ CERCA (no exacto)
        Permite señales cuando:
        - Precio rebota DESDE un nivel
        - Precio se acerca A un nivel desde cierta distancia
        """
        
        for level_data in levels[:5]:  # Top 5 niveles
            level = level_data['level']
            level_type = level_data['type']
            touches = level_data['touches']
            
            distance_pips = abs(current_price - level) / 0.01
            
            # ✅ MEJORA 1: Aceptar si está CERCA del nivel
            # (dentro del 200% de la tolerancia)
            if distance_pips <= self.tolerance_pips * 2.0:
                
                # ✅ MEJORA 2: Evitar señales repetidas del mismo nivel
                if (self.last_signal_level == level and 
                    self.last_signal_time and
                    (datetime.now() - self.last_signal_time).total_seconds() < 300):
                    continue  # Esperar 5 minutos antes de otra del mismo nivel
                
                # Determinar dirección según tipo de nivel
                if level_type == 'resistance':
                    # Esperamos rechazo de resistance (SELL)
                    if current_price >= level - self.tolerance_pips * 0.015:
                        signal = -1
                    else:
                        continue  # Aún no está en posición de rechazo
                else:  # support
                    # Esperamos rechazo de support (BUY)
                    if current_price <= level + self.tolerance_pips * 0.015:
                        signal = 1
                    else:
                        continue  # Aún no está en posición de rechazo
                
                # ✅ Confianza según fuerza del nivel
                confidence = 0.62 + min((touches - 2) * 0.08, 0.15)
                confidence = min(confidence, 0.80)
                
                self.last_signal_level = level
                self.last_signal_time = datetime.now()
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': f"S/R: Nivel {level_type.upper()} ({touches} toques) @ {level:.2f}",
                    'sl_pips': 40,  # SL más ajustado en S/R
                    'tp_pips': 90,  # TP proporcional
                    'level_strength': touches,
                    'level_value': level
                }
        
        return None
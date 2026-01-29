"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   ESTRATEGIA SUPPORT/RESISTANCE v5.2                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from config import SR_LOOKBACK_BARS, SR_MIN_TOUCHES, SR_TOLERANCE_PIPS


class SupportResistanceSystem:
    """Sistema de Trading basado en Soporte y Resistencia"""
    
    def __init__(self, lookback_bars=SR_LOOKBACK_BARS, 
                 min_touches=SR_MIN_TOUCHES, 
                 tolerance_pips=SR_TOLERANCE_PIPS):
        self.lookback_bars = lookback_bars
        self.min_touches = min_touches
        self.tolerance_pips = tolerance_pips
        self.enabled = True
        
        self.cached_levels = []
        self.last_calculation = None
    
    def find_support_resistance_levels(self, df):
        if len(df) < self.lookback_bars:
            return []
        
        recent = df.tail(self.lookback_bars).copy()
        levels = []
        
        # Buscar niveles de resistencia (máximos locales)
        for i in range(2, len(recent)-2):
            current_high = recent['high'].iloc[i]
            
            if (current_high > recent['high'].iloc[i-1] and
                current_high > recent['high'].iloc[i-2] and
                current_high > recent['high'].iloc[i+1] and
                current_high > recent['high'].iloc[i+2]):
                
                levels.append({'price': float(current_high), 'type': 'resistance', 'strength': 1})
        
        # Buscar niveles de soporte (mínimos locales)
        for i in range(2, len(recent)-2):
            current_low = recent['low'].iloc[i]
            
            if (current_low < recent['low'].iloc[i-1] and
                current_low < recent['low'].iloc[i-2] and
                current_low < recent['low'].iloc[i+1] and
                current_low < recent['low'].iloc[i+2]):
                
                levels.append({'price': float(current_low), 'type': 'support', 'strength': 1})
        
        # Validar y agrupar niveles
        validated_levels = self._cluster_and_validate(levels)
        return validated_levels
    
    def _cluster_and_validate(self, levels):
        if not levels:
            return []
        
        tolerance = self.tolerance_pips * 0.01
        clustered = []
        
        # Agrupar niveles cercanos
        for level in levels:
            found = False
            for cluster in clustered:
                distance = abs(level['price'] - cluster['price'])
                
                if distance <= tolerance and level['type'] == cluster['type']:
                    cluster['touches'] += 1
                    cluster['price'] = (cluster['price'] * (cluster['touches']-1) + level['price']) / cluster['touches']
                    cluster['strength'] += 1
                    found = True
                    break
            
            if not found:
                clustered.append({
                    'price': level['price'],
                    'type': level['type'],
                    'touches': 1,
                    'strength': level['strength']
                })
        
        # Filtrar por número mínimo de toques
        validated = [l for l in clustered if l['touches'] >= self.min_touches]
        validated.sort(key=lambda x: x['touches'], reverse=True)
        
        return validated
    
    def get_signal(self, df, current_price):
        if not self.enabled:
            return None
        
        # Recalcular niveles cada 5 minutos
        now = datetime.now()
        if (self.last_calculation is None or 
            (now - self.last_calculation).total_seconds() > 300):
            
            self.cached_levels = self.find_support_resistance_levels(df)
            self.last_calculation = now
        
        levels = self.cached_levels
        
        if not levels:
            return None
        
        # Buscar niveles cercanos al precio actual
        for level in levels:
            distance_pips = abs(current_price - level['price']) / 0.01
            
            if distance_pips < 10:  # Dentro de 10 pips del nivel
                
                if level['type'] == 'support':
                    # Señal de compra en soporte
                    confidence = min(0.65 + (level['touches'] * 0.05), 0.85)
                    
                    return {
                        'signal': 1,
                        'confidence': confidence,
                        'reason': f"S/R: Soporte ${level['price']:.2f} ({level['touches']} toques)",
                        'sl_pips': 30,
                        'tp_pips': self._calculate_tp_distance(levels, current_price, 'support'),
                        'level_strength': level['touches']
                    }
                
                elif level['type'] == 'resistance':
                    # Señal de venta en resistencia
                    confidence = min(0.65 + (level['touches'] * 0.05), 0.85)
                    
                    return {
                        'signal': -1,
                        'confidence': confidence,
                        'reason': f"S/R: Resistencia ${level['price']:.2f} ({level['touches']} toques)",
                        'sl_pips': 30,
                        'tp_pips': self._calculate_tp_distance(levels, current_price, 'resistance'),
                        'level_strength': level['touches']
                    }
        
        return None
    
    def _calculate_tp_distance(self, levels, current_price, from_type):
        """Calcula distancia al siguiente nivel para TP"""
        if from_type == 'support':
            # Buscar siguiente resistencia
            resistances = [l['price'] for l in levels 
                          if l['type'] == 'resistance' and l['price'] > current_price]
            
            if resistances:
                target = min(resistances)
                distance_pips = (target - current_price) / 0.01
                return max(60, min(int(distance_pips - 3), 200))
            
            return 100
        
        else:  # from resistance
            # Buscar siguiente soporte
            supports = [l['price'] for l in levels 
                       if l['type'] == 'support' and l['price'] < current_price]
            
            if supports:
                target = max(supports)
                distance_pips = (current_price - target) / 0.01
                return max(60, min(int(distance_pips - 3), 200))
            
            return 100
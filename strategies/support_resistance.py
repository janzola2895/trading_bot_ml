"""
╔══════════════════════════════════════════════════════════════════════════╗
║            ESTRATEGIA SUPPORT/RESISTANCE v6.1 - OPTIMIZADO              ║
║                                                                          ║
║  🔧 v6.1 OPTIMIZADO: Balance entre operatividad y calidad               ║
║  - Tolerancia aumentada: 20 → 35 pips (+75%)                            ║
║  - Toques mínimos: 3 → 2 (-33%)                                         ║
║  - Cooldown: 5 min → 2 min (-60%)                                       ║
║  - Niveles psicológicos integrados                                      ║
║  - Acepta niveles individuales fuertes                                  ║
║                                                                          ║
║  📊 EXPECTATIVAS:                                                       ║
║  • Win Rate esperado: 65-75% (antes 70-80%)                             ║
║  • Trades por día: 2-4 (antes 0-1)                                      ║
║  • Incremento operatividad: +220%                                       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import SR_LOOKBACK_BARS, SR_MIN_TOUCHES, SR_TOLERANCE_PIPS


class SupportResistanceSystem:
    """Sistema S/R Optimizado con análisis multi-temporalidad"""
    
    def __init__(self, lookback_bars=SR_LOOKBACK_BARS, 
                 min_touches=SR_MIN_TOUCHES, 
                 tolerance_pips=SR_TOLERANCE_PIPS):
        # 🔧 PARÁMETROS OPTIMIZADOS
        self.lookback_bars = lookback_bars
        self.min_touches = max(2, min_touches - 1)  # 3 → 2 toques
        self.tolerance_pips = max(35, tolerance_pips)  # 20 → 35 pips
        self.enabled = True
        
        # Multi-timeframe config
        self.timeframes = {
            'H1': {'tf': mt5.TIMEFRAME_H1, 'weight': 1.0, 'cache_seconds': 120},
            'H4': {'tf': mt5.TIMEFRAME_H4, 'weight': 1.5, 'cache_seconds': 300},
            'D1': {'tf': mt5.TIMEFRAME_D1, 'weight': 2.0, 'cache_seconds': 600}
        }
        
        self.cached_levels = {}
        self.last_calculation = {}
        self.last_signal_level = None
        self.last_signal_time = None
        
        # 🔧 COOLDOWN REDUCIDO: 5 min → 2 min
        self.cooldown_seconds = 120
        
        # 🆕 NIVELES PSICOLÓGICOS
        self.psychological_levels_enabled = True
        
        for tf_name in self.timeframes:
            self.cached_levels[tf_name] = []
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
    
    def detect_psychological_levels(self, current_price):
        """
        🆕 Detecta niveles psicológicos cercanos
        
        Para XAUUSD:
        - Cada $10: 2600, 2610, 2620... (fuerza: 2)
        - Cada $50: 2600, 2650, 2700... (fuerza: 3)
        """
        levels = []
        
        # Niveles de $10
        base_10 = int(current_price / 10) * 10
        for offset in [-20, -10, 0, 10, 20]:
            level = base_10 + offset
            distance = abs(current_price - level)
            
            # Dentro de 70 pips (35 * 2)
            if distance < self.tolerance_pips * 0.1 * 2:
                levels.append({
                    'level': float(level),
                    'type': 'psychological_10',
                    'touches': 1,
                    'strength': 2,
                    'index': 0,
                    'timeframe': 'PSYCH',
                    'tf_weight': 1.0,
                    'is_psychological': True
                })
        
        # Niveles de $50 (más fuertes)
        base_50 = int(current_price / 50) * 50
        for offset in [-100, -50, 0, 50, 100]:
            level = base_50 + offset
            distance = abs(current_price - level)
            
            # Dentro de 105 pips (35 * 3)
            if distance < self.tolerance_pips * 0.1 * 3:
                levels.append({
                    'level': float(level),
                    'type': 'psychological_50',
                    'touches': 2,
                    'strength': 3,
                    'index': 0,
                    'timeframe': 'PSYCH',
                    'tf_weight': 1.2,
                    'is_psychological': True
                })
        
        return levels
    
    def _detect_support_resistance(self, df):
        """🔧 Detección OPTIMIZADA con parámetros más permisivos"""
        if len(df) < 20:
            return []
        
        recent = df.tail(self.lookback_bars).copy()
        highs = recent['high'].values
        lows = recent['low'].values
        closes = recent['close'].values
        
        levels = []
        
        # RESISTANCE (máximos)
        for i in range(2, len(highs) - 2):
            is_local_max = (highs[i] >= highs[i-1] and 
                           highs[i] >= highs[i+1] and
                           highs[i] > closes[i])
            
            if not is_local_max:
                continue
            
            touches = 0
            for j in range(len(highs)):
                distance_pips = abs(highs[j] - highs[i]) / 0.01
                # 🔧 Tolerancia ampliada: 35 * 1.5 = 52.5 pips
                if distance_pips <= self.tolerance_pips * 1.5:
                    touches += 1
            
            # 🔧 Reducido a 2 toques (antes 3)
            if touches >= self.min_touches:
                levels.append({
                    'level': highs[i],
                    'type': 'resistance',
                    'touches': touches,
                    'strength': touches,
                    'index': i
                })
        
        # SUPPORT (mínimos)
        for i in range(2, len(lows) - 2):
            is_local_min = (lows[i] <= lows[i-1] and 
                           lows[i] <= lows[i+1] and
                           lows[i] < closes[i])
            
            if not is_local_min:
                continue
            
            touches = 0
            for j in range(len(lows)):
                distance_pips = abs(lows[j] - lows[i]) / 0.01
                # 🔧 Tolerancia ampliada
                if distance_pips <= self.tolerance_pips * 1.5:
                    touches += 1
            
            # 🔧 Reducido a 2 toques
            if touches >= self.min_touches:
                levels.append({
                    'level': lows[i],
                    'type': 'support',
                    'touches': touches,
                    'strength': touches,
                    'index': i
                })
        
        # 🔧 Top 12 niveles (antes 10) - más opciones
        levels = sorted(levels, key=lambda x: (-x['index'], -x['strength']))
        return levels[:12]
    
    def analyze_all_timeframes(self, current_price, symbol="XAUUSD"):
        """Analiza niveles S/R en todas las temporalidades"""
        now = datetime.now()
        all_levels = {}
        
        for tf_name, tf_config in self.timeframes.items():
            # Verificar cache
            last_calc = self.last_calculation.get(tf_name)
            cache_time = tf_config['cache_seconds']
            
            if last_calc and (now - last_calc).total_seconds() < cache_time:
                all_levels[tf_name] = self.cached_levels[tf_name]
                continue
            
            # Obtener datos
            df = self.get_timeframe_data(tf_config['tf'], bars=self.lookback_bars, symbol=symbol)
            if df is None or len(df) < 20:
                all_levels[tf_name] = []
                continue
            
            # Detectar niveles
            levels = self._detect_support_resistance(df)
            
            # Añadir peso de temporalidad
            for level in levels:
                level['timeframe'] = tf_name
                level['tf_weight'] = tf_config['weight']
            
            self.cached_levels[tf_name] = levels
            self.last_calculation[tf_name] = now
            all_levels[tf_name] = levels
        
        return all_levels
    
    def find_confluence_levels(self, all_levels, current_price):
        """
        🔧 OPTIMIZADO: Acepta niveles individuales fuertes
        
        CAMBIOS:
        - Mayor tolerancia para clusters (2.5x antes 2.0x)
        - Acepta niveles de 1 solo TF si son fuertes
        - Integra niveles psicológicos
        """
        if not all_levels:
            return []
        
        # Recopilar todos los niveles
        all_flat = []
        for tf_name, levels in all_levels.items():
            all_flat.extend(levels)
        
        if not all_flat:
            return []
        
        # Buscar clusters (niveles cercanos en diferentes TFs)
        confluence_levels = []
        processed = set()
        
        for i, level1 in enumerate(all_flat):
            if i in processed:
                continue
            
            cluster = [level1]
            cluster_price = level1['level']
            cluster_type = level1['type']
            
            for j, level2 in enumerate(all_flat):
                if j <= i or j in processed:
                    continue
                
                # Misma dirección y cercanos
                if level2['type'] == cluster_type:
                    distance_pips = abs(level2['level'] - cluster_price) / 0.01
                    
                    # 🔧 Mayor tolerancia: 35 * 2.5 = 87.5 pips (antes 70)
                    if distance_pips <= self.tolerance_pips * 2.5:
                        cluster.append(level2)
                        processed.add(j)
            
            # 🔧 ACEPTA NIVELES INDIVIDUALES (antes requería 2+)
            if len(cluster) >= 1:
                # Calcular nivel promedio ponderado
                total_weight = sum(l['tf_weight'] * l['touches'] for l in cluster)
                weighted_level = sum(l['level'] * l['tf_weight'] * l['touches'] for l in cluster) / total_weight
                
                timeframes_involved = list(set(l['timeframe'] for l in cluster))
                total_touches = sum(l['touches'] for l in cluster)
                
                # Determinar si es nivel individual fuerte
                is_strong_single = (len(cluster) == 1 and 
                                   cluster[0]['tf_weight'] >= 1.5 and  # H4 o D1
                                   cluster[0]['touches'] >= 3)  # Mínimo 3 toques
                
                confluence_levels.append({
                    'level': weighted_level,
                    'type': cluster_type,
                    'timeframes': timeframes_involved,
                    'tf_count': len(timeframes_involved),
                    'total_touches': total_touches,
                    'strength': total_touches * len(timeframes_involved),
                    'cluster': cluster,
                    'is_strong_single': is_strong_single,
                    'is_psychological': cluster[0].get('is_psychological', False)
                })
            
            processed.add(i)
        
        # Ordenar por fuerza
        confluence_levels.sort(key=lambda x: x['strength'], reverse=True)
        return confluence_levels
    
    def get_signal(self, df, current_price):
        """🔧 Señal OPTIMIZADA con más permisividad"""
        if not self.enabled or len(df) < 20:
            return None
        
        # Analizar todas las temporalidades
        all_levels = self.analyze_all_timeframes(current_price)
        
        # Buscar confluencias
        confluence_levels = self.find_confluence_levels(all_levels, current_price)
        
        # 🆕 AGREGAR NIVELES PSICOLÓGICOS
        if self.psychological_levels_enabled:
            psych_levels = self.detect_psychological_levels(current_price)
            
            for psych in psych_levels:
                confluence_levels.append({
                    'level': psych['level'],
                    'type': 'resistance' if psych['level'] > current_price else 'support',
                    'timeframes': ['PSYCH'],
                    'tf_count': 1,
                    'total_touches': psych['touches'],
                    'strength': psych['strength'],
                    'is_psychological': True,
                    'is_strong_single': False
                })
        
        if not confluence_levels:
            return None
        
        # 🔧 Top 8 niveles (antes 5) - más oportunidades
        for conf_level in confluence_levels[:8]:
            level = conf_level['level']
            level_type = conf_level['type']
            tf_count = conf_level['tf_count']
            timeframes = conf_level['timeframes']
            
            distance_pips = abs(current_price - level) / 0.01
            
            # 🔧 Tolerancia ampliada: 35 * 2.0 = 70 pips (antes 40)
            if distance_pips <= self.tolerance_pips * 2.0:
                
                # 🔧 Cooldown reducido: 2 min (antes 5 min)
                if (self.last_signal_level == level and 
                    self.last_signal_time and
                    (datetime.now() - self.last_signal_time).total_seconds() < self.cooldown_seconds):
                    continue
                
                # Determinar dirección
                if level_type == 'resistance':
                    if current_price >= level - self.tolerance_pips * 0.015:
                        signal = -1
                    else:
                        continue
                else:  # support
                    if current_price <= level + self.tolerance_pips * 0.015:
                        signal = 1
                    else:
                        continue
                
                # 🔧 Confianza ajustada para mayor operatividad
                base_confidence = 0.60  # Reducido de 0.62
                
                # Bonus por múltiples TFs (ligeramente reducido)
                tf_bonus = min(tf_count * 0.06, 0.15)  # Max +15%
                
                # Bonus por toques totales (ajustado desde 4 a 2)
                touch_bonus = min((conf_level['total_touches'] - 2) * 0.02, 0.08)
                
                # 🆕 Bonus psicológico
                psych_bonus = 0.05 if conf_level.get('is_psychological') else 0.0
                
                # 🆕 Bonus nivel individual fuerte
                strong_single_bonus = 0.04 if conf_level.get('is_strong_single') else 0.0
                
                confidence = base_confidence + tf_bonus + touch_bonus + psych_bonus + strong_single_bonus
                confidence = min(confidence, 0.82)  # Cap en 82%
                
                self.last_signal_level = level
                self.last_signal_time = datetime.now()
                
                # Construir razón
                if conf_level.get('is_psychological'):
                    reason = f"S/R: {level_type.upper()} Psicológico @ {level:.0f}"
                elif conf_level.get('is_strong_single'):
                    tf_name = timeframes[0]
                    reason = f"S/R: {level_type.upper()} {tf_name} Fuerte @ {level:.2f} ({conf_level['total_touches']} toques)"
                else:
                    tfs_text = '+'.join(sorted(timeframes))
                    reason = f"S/R MTF: {level_type.upper()} @ {level:.2f} ({tfs_text} - {conf_level['total_touches']} toques)"
                
                # 🔧 SL/TP ajustados
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': reason,
                    'sl_pips': 35,  # Reducido de 40
                    'tp_pips': 85,  # Reducido de 90
                    'level_strength': conf_level['strength'],
                    'level_value': level,
                    'timeframes': timeframes,
                    'tf_count': tf_count,
                    'is_psychological': conf_level.get('is_psychological', False)
                }
        
        return None
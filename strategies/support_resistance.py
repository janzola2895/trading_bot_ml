"""
╔══════════════════════════════════════════════════════════════════════════╗
║            ESTRATEGIA SUPPORT/RESISTANCE v6.0 - MULTI-TIMEFRAME         ║
║                                                                          ║
║  🆕 v6.0: Análisis multi-temporalidad                                   ║
║  - Detecta niveles S/R en H1, H4, D1                                    ║
║  - Mayor confianza cuando niveles coinciden en múltiples TFs            ║
║  - Prioriza niveles validados en temporalidades superiores             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from config import SR_LOOKBACK_BARS, SR_MIN_TOUCHES, SR_TOLERANCE_PIPS


class SupportResistanceSystem:
    """Sistema S/R con análisis multi-temporalidad"""
    
    def __init__(self, lookback_bars=SR_LOOKBACK_BARS, 
                 min_touches=SR_MIN_TOUCHES, 
                 tolerance_pips=SR_TOLERANCE_PIPS):
        self.lookback_bars = lookback_bars
        self.min_touches = max(2, min_touches)
        self.tolerance_pips = tolerance_pips
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
    
    def _detect_support_resistance(self, df):
        """Detecta niveles S/R en un dataframe"""
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
                if distance_pips <= self.tolerance_pips * 1.5:
                    touches += 1
            
            if touches >= max(2, self.min_touches - 1):
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
        
        levels = sorted(levels, key=lambda x: (-x['index'], -x['strength']))
        return levels[:10]
    
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
        """Encuentra niveles con confluencia multi-temporalidad"""
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
                    
                    if distance_pips <= self.tolerance_pips * 2.0:
                        cluster.append(level2)
                        processed.add(j)
            
            if len(cluster) >= 2:  # Al menos 2 TFs coinciden
                # Calcular nivel promedio ponderado
                total_weight = sum(l['tf_weight'] * l['touches'] for l in cluster)
                weighted_level = sum(l['level'] * l['tf_weight'] * l['touches'] for l in cluster) / total_weight
                
                timeframes_involved = list(set(l['timeframe'] for l in cluster))
                total_touches = sum(l['touches'] for l in cluster)
                
                confluence_levels.append({
                    'level': weighted_level,
                    'type': cluster_type,
                    'timeframes': timeframes_involved,
                    'tf_count': len(timeframes_involved),
                    'total_touches': total_touches,
                    'strength': total_touches * len(timeframes_involved),
                    'cluster': cluster
                })
            
            processed.add(i)
        
        # Ordenar por fuerza
        confluence_levels.sort(key=lambda x: x['strength'], reverse=True)
        return confluence_levels
    
    def get_signal(self, df, current_price):
        """Genera señal basada en análisis multi-temporalidad"""
        if not self.enabled or len(df) < 20:
            return None
        
        # Analizar todas las temporalidades
        all_levels = self.analyze_all_timeframes(current_price)
        
        # Buscar confluencias
        confluence_levels = self.find_confluence_levels(all_levels, current_price)
        
        if not confluence_levels:
            return None
        
        # Buscar nivel cercano al precio actual
        for conf_level in confluence_levels[:5]:  # Top 5
            level = conf_level['level']
            level_type = conf_level['type']
            tf_count = conf_level['tf_count']
            timeframes = conf_level['timeframes']
            
            distance_pips = abs(current_price - level) / 0.01
            
            # Dentro de rango
            if distance_pips <= self.tolerance_pips * 2.0:
                
                # Evitar señales repetidas
                if (self.last_signal_level == level and 
                    self.last_signal_time and
                    (datetime.now() - self.last_signal_time).total_seconds() < 300):
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
                
                # Confianza según confluencia
                base_confidence = 0.62
                
                # Bonus por múltiples TFs
                tf_bonus = min(tf_count * 0.08, 0.20)  # Max +20%
                
                # Bonus por toques totales
                touch_bonus = min((conf_level['total_touches'] - 4) * 0.03, 0.10)
                
                confidence = base_confidence + tf_bonus + touch_bonus
                confidence = min(confidence, 0.85)
                
                self.last_signal_level = level
                self.last_signal_time = datetime.now()
                
                tfs_text = '+'.join(sorted(timeframes))
                
                return {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': f"S/R MTF: {level_type.upper()} @ {level:.2f} ({tfs_text} - {conf_level['total_touches']} toques)",
                    'sl_pips': 40,
                    'tp_pips': 90,
                    'level_strength': conf_level['strength'],
                    'level_value': level,
                    'timeframes': timeframes,
                    'tf_count': tf_count
                }
        
        return None
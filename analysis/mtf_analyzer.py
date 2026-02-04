"""
╔══════════════════════════════════════════════════════════════════════════╗
║          SISTEMA MULTI-TIMEFRAME (MTF) v7.0 CONFIGURABLE FIXED          ║
║                                                                          ║
║  🆕 SISTEMA CONFIGURABLE: 6 temporalidades seleccionables               ║
║  ✅ COMPATIBLE con main.py existente (atributo 'timeframes')            ║
║  - Usuario selecciona qué TFs deben estar activos                       ║
║  - TODAS las TFs activas deben tener el mismo bias                      ║
║  - Bullish → BUY aprobado | Bearish → SELL aprobado                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
import ta
from datetime import datetime


class MultiTimeframeAnalyzer:
    """
    Sistema MTF CONFIGURABLE v7.0 - 6 Temporalidades
    
    🆕 NUEVA LÓGICA:
    - Usuario selecciona qué temporalidades quiere analizar (checkboxes GUI)
    - TODAS las temporalidades activas deben coincidir en dirección
    - Si todas son bullish → BUY aprobado
    - Si todas son bearish → SELL aprobado
    - Si hay mezcla o neutrales → BLOQUEADO
    
    EJEMPLOS:
    - Activas: [W1, H4, H1] → Las 3 deben ser bullish para BUY
    - Activas: [H1, M30] → Las 2 deben coincidir
    - Activas: [W1] → Solo W1 decide
    - Activas: [] → TODO bloqueado
    """
    
    def __init__(self, symbol="XAUUSD", logger=None):
        self.symbol = symbol
        self.logger = logger
        
        # ✅ COMPATIBILIDAD: Usar 'timeframes' en lugar de 'available_timeframes'
        # para que main.py funcione correctamente
        self.timeframes = {
            'M15': {
                'tf': mt5.TIMEFRAME_M15,
                'update_interval': 30,  # Actualizar cada 30s
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  # Por defecto inactivo
            },
            'M30': {
                'tf': mt5.TIMEFRAME_M30,
                'update_interval': 60,  # Actualizar cada 60s
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False
            },
            'H1': {
                'tf': mt5.TIMEFRAME_H1,
                'update_interval': 120,  # Actualizar cada 2min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  # ✅ Activo por defecto
            },
            'H4': {
                'tf': mt5.TIMEFRAME_H4,
                'update_interval': 300,  # Actualizar cada 5min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  # ✅ Activo por defecto
            },
            'D1': {
                'tf': mt5.TIMEFRAME_D1,
                'update_interval': 600,  # Actualizar cada 10min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': True
            },
            'W1': {
                'tf': mt5.TIMEFRAME_W1,
                'update_interval': 600,  # Actualizar cada 10min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  # ✅ Activo por defecto
            }
        }
        
        # Estadísticas
        self.stats = {
            'total_analysis': 0,
            'operations_blocked': 0,
            'operations_approved': 0,
            'bullish_approvals': 0,
            'bearish_approvals': 0
        }
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def update_active_timeframes(self, active_tf_list):
        """
        🔧 CORREGIDO: Actualiza qué temporalidades están activas Y LIMPIA CACHÉ
        
        Args:
            active_tf_list: Lista de nombres de TFs activos ['H1', 'H4', 'W1']
        """
        # Desactivar todas primero Y LIMPIAR CACHÉ COMPLETAMENTE
        for tf_name in self.timeframes:
            self.timeframes[tf_name]['active'] = False
            # 🔧 CRÍTICO: LIMPIAR CACHÉ COMPLETAMENTE (no solo last_update)
            self.timeframes[tf_name]['last_update'] = None
            self.timeframes[tf_name]['bias'] = 'neutral'
            self.timeframes[tf_name]['strength'] = 0.0
            self.timeframes[tf_name]['indicators'] = {}
        
        # Activar solo las seleccionadas
        for tf_name in active_tf_list:
            if tf_name in self.timeframes:
                self.timeframes[tf_name]['active'] = True
        
        active_count = len(active_tf_list)
        self.send_log(f"📊 MTF Config actualizado: {active_count} temporalidad(es) activas: {', '.join(active_tf_list)}")
        self.send_log(f"🔧 Caché MTF limpiado - Forzando re-análisis inmediato...")
        
    def get_active_timeframes(self):
        """Retorna lista de temporalidades activas"""
        return [tf_name for tf_name, config in self.timeframes.items() if config['active']]
    
    def get_timeframe_data(self, tf, bars=100):
        """Obtiene datos de un timeframe específico"""
        try:
            rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, bars)
            if rates is None:
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except Exception as e:
            self.send_log(f"⚠️ Error obteniendo datos: {e}")
            return None
    
    def calculate_timeframe_indicators(self, df):
        """Calcula indicadores para un timeframe"""
        df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema_100'] = ta.trend.ema_indicator(df['close'], window=100)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        
        df.dropna(inplace=True)
        return df
    
    def analyze_single_timeframe(self, tf_name):
        """
        Analiza un timeframe individual
        
        Returns:
            dict: {'bias': 'bullish'|'bearish'|'neutral', 'strength': 0.0-1.0}
        """
        tf_config = self.timeframes[tf_name]
        
        # Verificar si necesita actualización
        now = datetime.now()
        if (tf_config['last_update'] is not None and 
            (now - tf_config['last_update']).total_seconds() < tf_config['update_interval']):
            # Usar caché
            return {
                'bias': tf_config['bias'],
                'strength': tf_config['strength'],
                'cached': True
            }
        
        # Obtener datos frescos
        df = self.get_timeframe_data(tf_config['tf'], bars=100)
        if df is None or len(df) < 50:
            return {'bias': 'neutral', 'strength': 0.0, 'error': True}
        
        df = self.calculate_timeframe_indicators(df)
        last_row = df.iloc[-1]
        
        # === ANÁLISIS DE TENDENCIA ===
        
        # 1. EMAs (peso: 40%)
        ema_bullish = last_row['ema_21'] > last_row['ema_50'] > last_row['ema_100']
        ema_bearish = last_row['ema_21'] < last_row['ema_50'] < last_row['ema_100']
        
        ema_score = 0
        if ema_bullish:
            ema_diff_pct = (last_row['ema_21'] - last_row['ema_50']) / last_row['ema_50']
            ema_score = min(0.40, ema_diff_pct * 100 * 0.40)
        elif ema_bearish:
            ema_diff_pct = (last_row['ema_50'] - last_row['ema_21']) / last_row['ema_50']
            ema_score = -min(0.40, ema_diff_pct * 100 * 0.40)
        
        # 2. MACD (peso: 30%)
        macd_bullish = last_row['macd'] > last_row['macd_signal'] and last_row['macd'] > 0
        macd_bearish = last_row['macd'] < last_row['macd_signal'] and last_row['macd'] < 0
        
        macd_score = 0
        if macd_bullish:
            macd_score = 0.30
        elif macd_bearish:
            macd_score = -0.30
        
        # 3. ADX (fuerza de tendencia, peso: 30%)
        adx_strength = min(last_row['adx'] / 50, 1.0)
        
        # Calcular score total
        total_score = ema_score + macd_score
        
        # Aplicar fuerza de tendencia
        total_score *= adx_strength
        
        # Determinar bias
        if total_score > 0.15:
            bias = "bullish"
            strength = min(abs(total_score), 1.0)
        elif total_score < -0.15:
            bias = "bearish"
            strength = min(abs(total_score), 1.0)
        else:
            bias = "neutral"
            strength = abs(total_score)
        
        # Actualizar caché
        tf_config['bias'] = bias
        tf_config['strength'] = strength
        tf_config['last_update'] = now
        tf_config['indicators'] = {
            'ema_21': float(last_row['ema_21']),
            'ema_50': float(last_row['ema_50']),
            'ema_100': float(last_row['ema_100']),
            'adx': float(last_row['adx']),
            'rsi': float(last_row['rsi']),
            'macd': float(last_row['macd']),
            'ema_score': ema_score,
            'macd_score': macd_score,
            'total_score': total_score
        }
        
        return {
            'bias': bias,
            'strength': strength,
            'indicators': tf_config['indicators']
        }
    
    def analyze_all_timeframes(self):
        """
        🆕 LÓGICA CONFIGURABLE v7.0
        
        REGLA: TODAS las temporalidades ACTIVAS deben coincidir
        - Si todas son bullish → BUY aprobado
        - Si todas son bearish → SELL aprobado
        - Si hay mezcla o neutral → BLOQUEADO
        """
        self.stats['total_analysis'] += 1
        
        # Obtener temporalidades activas
        active_tfs = self.get_active_timeframes()
        
        # Si no hay ninguna activa, bloquear todo
        if len(active_tfs) == 0:
            self.stats['operations_blocked'] += 1
            return {
                'approved': False,
                'direction': None,
                'active_timeframes': [],
                'reason': 'No hay temporalidades activas',
                'timeframes_detail': {}
            }
        
        # Analizar solo las activas
        results = {}
        biases = []
        
        for tf_name in active_tfs:
            analysis = self.analyze_single_timeframe(tf_name)
            results[tf_name] = analysis
            biases.append(analysis['bias'])
        
        # 🆕 VERIFICAR UNANIMIDAD
        
        # Verificar si TODAS son bullish
        all_bullish = all(bias == 'bullish' for bias in biases)
        
        # Verificar si TODAS son bearish
        all_bearish = all(bias == 'bearish' for bias in biases)
        
        approved = False
        direction = None
        
        if all_bullish:
            # ✅ TODAS BULLISH → APROBAR BUY
            approved = True
            direction = 'buy'
            self.stats['operations_approved'] += 1
            self.stats['bullish_approvals'] += 1
        
        elif all_bearish:
            # ✅ TODAS BEARISH → APROBAR SELL
            approved = True
            direction = 'sell'
            self.stats['operations_approved'] += 1
            self.stats['bearish_approvals'] += 1
        
        else:
            # ❌ HAY MEZCLA O NEUTRALES → BLOQUEAR
            self.stats['operations_blocked'] += 1
        
        return {
            'approved': approved,
            'direction': direction,
            'active_timeframes': active_tfs,
            'aligned_timeframes': active_tfs if approved else [],
            'timeframes_detail': results,
            'bias_summary': biases
        }
    
    def check_signal_alignment(self, signal_type):
        """
        Verifica si una señal está alineada con el análisis MTF
        
        Args:
            signal_type: 1 (buy) o -1 (sell)
        
        Returns:
            dict: {'allowed': bool, 'reason': str, 'mtf_analysis': {...}}
        """
        mtf_analysis = self.analyze_all_timeframes()
        
        if not mtf_analysis['approved']:
            active_tfs = mtf_analysis['active_timeframes']
            bias_summary = mtf_analysis.get('bias_summary', [])
            
            if len(active_tfs) == 0:
                return {
                    'allowed': False,
                    'reason': "MTF: Sin temporalidades activas",
                    'mtf_analysis': mtf_analysis
                }
            
            # Mostrar qué bias tiene cada TF
            tf_bias_pairs = [f"{tf}:{bias[:4].upper()}" for tf, bias in zip(active_tfs, bias_summary)]
            bias_text = " / ".join(tf_bias_pairs)
            
            return {
                'allowed': False,
                'reason': f"MTF: Sin alineación ({bias_text})",
                'mtf_analysis': mtf_analysis
            }
        
        # Verificar dirección
        if signal_type == 1 and mtf_analysis['direction'] == 'buy':
            active_tfs = mtf_analysis['active_timeframes']
            tfs_text = '+'.join(active_tfs)
            
            return {
                'allowed': True,
                'reason': f"MTF: ✅ BUY Aprobado ({tfs_text})",
                'mtf_analysis': mtf_analysis
            }
        
        elif signal_type == -1 and mtf_analysis['direction'] == 'sell':
            active_tfs = mtf_analysis['active_timeframes']
            tfs_text = '+'.join(active_tfs)
            
            return {
                'allowed': True,
                'reason': f"MTF: ✅ SELL Aprobado ({tfs_text})",
                'mtf_analysis': mtf_analysis
            }
        
        else:
            direction_name = "BUY" if signal_type == 1 else "SELL"
            mtf_direction = mtf_analysis['direction'].upper()
            
            return {
                'allowed': False,
                'reason': f"MTF: ⛔ {direction_name} bloqueado (MTF aprueba {mtf_direction})",
                'mtf_analysis': mtf_analysis
            }
    
    def get_stats(self):
        """Retorna estadísticas del sistema MTF"""
        total = self.stats['operations_approved'] + self.stats['operations_blocked']
        approval_rate = (self.stats['operations_approved'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'approval_rate': approval_rate,
            'active_timeframes': self.get_active_timeframes()
        }
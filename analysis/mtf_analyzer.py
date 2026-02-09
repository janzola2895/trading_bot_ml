"""
╔══════════════════════════════════════════════════════════════════════════╗
║          SISTEMA MULTI-TIMEFRAME (MTF) v7.1 IMPROVED                    ║
║                                                                          ║
║  🆕 MEJORAS v7.1:                                                        ║
║  ✅ Umbral reducido: 0.15 → 0.05 (detecta tendencias reales)            ║
║  ✅ ADX optimizado: No elimina señales, solo modula                     ║
║  ✅ RSI agregado: 20% de peso adicional                                 ║
║  ✅ EMA más sensible: Detecta movimientos sutiles                       ║
║  ✅ MACD mejorado: Ponderación por diferencia de líneas                 ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
import ta
from datetime import datetime


class MultiTimeframeAnalyzer:
    """
    Sistema MTF MEJORADO v7.1 - 6 Temporalidades
    
    🆕 CORRECCIONES IMPLEMENTADAS:
    
    1. UMBRAL REALISTA:
       - Antes: total_score > 0.15 (demasiado alto)
       - Ahora: total_score > 0.05 (captura tendencias reales)
    
    2. ADX OPTIMIZADO:
       - Antes: ADX bajo eliminaba señales (ADX=10 → score × 0.2)
       - Ahora: ADX solo modula (ADX=10 → score × 0.5 mínimo)
    
    3. RSI AGREGADO:
       - Nuevo indicador con 20% de peso
       - RSI > 60 = bullish | RSI < 40 = bearish
    
    4. EMA MÁS SENSIBLE:
       - Multiplicador aumentado: × 200 (antes × 100)
       - Detecta separaciones sutiles entre medias
    
    5. MACD MEJORADO:
       - Ponderación por diferencia entre MACD y señal
       - No solo evalúa cruce, sino magnitud
    
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
                'active': True  # ✅ Activo por defecto
            },
            'H1': {
                'tf': mt5.TIMEFRAME_H1,
                'update_interval': 120,  # Actualizar cada 2min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  
            },
            'H4': {
                'tf': mt5.TIMEFRAME_H4,
                'update_interval': 300,  # Actualizar cada 5min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False  
            },
            'D1': {
                'tf': mt5.TIMEFRAME_D1,
                'update_interval': 600,  # Actualizar cada 10min
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {},
                'active': False
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
        🆕 ANÁLISIS MEJORADO v7.1
        
        Analiza un timeframe individual con lógica optimizada:
        - Umbral reducido: 0.05 (antes 0.15)
        - ADX modulador: No elimina señales
        - RSI agregado: 20% de peso
        - EMA más sensible: × 200
        - MACD ponderado: Por diferencia de líneas
        
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
        
        # === ANÁLISIS DE TENDENCIA MEJORADO v7.1 ===
        
        # 1. EMAs (peso: 50% - aumentado y más sensible)
        ema_21 = last_row['ema_21']
        ema_50 = last_row['ema_50']
        ema_100 = last_row['ema_100']
        
        ema_bullish = ema_21 > ema_50 > ema_100
        ema_bearish = ema_21 < ema_50 < ema_100
        
        ema_score = 0
        if ema_bullish:
            ema_diff_pct = (ema_21 - ema_50) / ema_50
            # ✅ MEJORADO: × 200 en lugar de × 100 (más sensible)
            ema_score = min(0.50, ema_diff_pct * 200)
        elif ema_bearish:
            ema_diff_pct = (ema_50 - ema_21) / ema_50
            ema_score = -min(0.50, ema_diff_pct * 200)
        
        # 2. MACD (peso: 30% - mejorado con ponderación por diferencia)
        macd = last_row['macd']
        macd_signal = last_row['macd_signal']
        
        macd_bullish = macd > macd_signal and macd > 0
        macd_bearish = macd < macd_signal and macd < 0
        
        macd_score = 0
        if macd_bullish:
            # ✅ MEJORADO: Ponderar por diferencia entre líneas
            macd_diff = abs(macd - macd_signal)
            macd_score = min(0.30, macd_diff * 0.5)
        elif macd_bearish:
            macd_diff = abs(macd - macd_signal)
            macd_score = -min(0.30, macd_diff * 0.5)
        
        # 3. RSI (peso: 20% - NUEVO INDICADOR)
        rsi = last_row['rsi']
        rsi_score = 0
        
        if rsi > 60:
            # RSI alcista: cuanto más alto, más bullish
            rsi_score = min(0.20, (rsi - 50) / 100)
        elif rsi < 40:
            # RSI bajista: cuanto más bajo, más bearish
            rsi_score = -min(0.20, (50 - rsi) / 100)
        
        # 4. ADX (modulador de fuerza - OPTIMIZADO)
        adx = last_row['adx']
        
        # ✅ MEJORADO: ADX solo modula, NO elimina señales
        if adx < 15:
            adx_multiplier = 0.5  # Reduce a 50% pero NO elimina
        elif adx < 25:
            adx_multiplier = 0.8  # Reduce a 80%
        else:
            adx_multiplier = 1.0  # Fuerza completa
        
        # Calcular score total
        total_score = (ema_score + macd_score + rsi_score) * adx_multiplier
        
        # ✅ UMBRAL CORREGIDO: 0.05 en lugar de 0.15
        if total_score > 0.05:
            bias = "bullish"
            strength = min(abs(total_score), 1.0)
        elif total_score < -0.05:
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
            'ema_21': float(ema_21),
            'ema_50': float(ema_50),
            'ema_100': float(ema_100),
            'adx': float(adx),
            'rsi': float(rsi),
            'macd': float(macd),
            'macd_signal': float(macd_signal),
            'ema_score': float(ema_score),
            'macd_score': float(macd_score),
            'rsi_score': float(rsi_score),
            'adx_multiplier': float(adx_multiplier),
            'total_score': float(total_score)
        }
        
        return {
            'bias': bias,
            'strength': strength,
            'indicators': tf_config['indicators']
        }
    
    def analyze_all_timeframes(self):
        """
        🆕 LÓGICA CONFIGURABLE v7.0 + MEJORAS v7.1
        
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
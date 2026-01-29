"""
╔══════════════════════════════════════════════════════════════════════════╗
║              SISTEMA MULTI-TIMEFRAME (MTF) v5.2                          ║
║                                                                          ║
║  Sistema de análisis en múltiples timeframes con prioridades            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
import pandas as pd
import ta
from datetime import datetime
from config import (
    MTF_TIMEFRAMES, MTF_REQUIRED_HIGHER_TF, MTF_REQUIRED_LOWER_TF
)


class MultiTimeframeAnalyzer:
    """
    Sistema de Análisis Multi-Timeframe con Ponderación
    
    CARACTERÍSTICAS:
    - Analiza M30, H1, H4, D1, W1
    - Ponderación: M30/H1 (lower), H4/D1/W1 (higher)
    - Requiere 2 de 3 superiores + 1 de 2 inferiores para aprobar
    - Actualización inteligente: M30/H1 cada 1min, H4/D1/W1 cada 5min
    - Bloqueo total de operaciones sin alineación suficiente
    """
    
    def __init__(self, symbol="XAUUSD", logger=None):
        self.symbol = symbol
        self.logger = logger
        
        # Configuración de timeframes y ponderación
        self.timeframes = {}
        for name, config in MTF_TIMEFRAMES.items():
            self.timeframes[name] = {
                **config,
                'last_update': None,
                'bias': 'neutral',
                'strength': 0.0,
                'indicators': {}
            }
        
        self.required_higher_tf = MTF_REQUIRED_HIGHER_TF
        self.required_lower_tf = MTF_REQUIRED_LOWER_TF
        
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
            self.send_log(f"⚠️ Error obteniendo datos {tf}: {e}")
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
        🆕 OPCIÓN C: Sistema con timeframes prioritarios
        
        REGLA: 2 de 3 superiores (H4/D1/W1) + 1 de 2 inferiores (M30/H1)
        """
        self.stats['total_analysis'] += 1
        
        results = {}
        
        # Separar timeframes
        higher_tfs = ['H4', 'D1', 'W1']
        lower_tfs = ['M30', 'H1']
        
        # Contadores de votos
        higher_votes = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        lower_votes = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        
        # Analizar cada timeframe
        for tf_name in ['M30', 'H1', 'H4', 'D1', 'W1']:
            analysis = self.analyze_single_timeframe(tf_name)
            results[tf_name] = analysis
            
            bias = analysis['bias']
            priority = self.timeframes[tf_name]['priority']
            
            # Contar votos según prioridad
            if priority == 'higher':
                higher_votes[bias] += 1
            else:
                lower_votes[bias] += 1
        
        # 🆕 LÓGICA DE APROBACIÓN - OPCIÓN C
        approved = False
        direction = None
        
        # Verificar BUY: 2+ superiores bullish Y 1+ inferiores bullish
        if (higher_votes['bullish'] >= self.required_higher_tf and 
            lower_votes['bullish'] >= self.required_lower_tf):
            approved = True
            direction = 'buy'
            self.stats['operations_approved'] += 1
            self.stats['bullish_approvals'] += 1
        
        # Verificar SELL: 2+ superiores bearish Y 1+ inferiores bearish
        elif (higher_votes['bearish'] >= self.required_higher_tf and 
            lower_votes['bearish'] >= self.required_lower_tf):
            approved = True
            direction = 'sell'
            self.stats['operations_approved'] += 1
            self.stats['bearish_approvals'] += 1
        
        else:
            self.stats['operations_blocked'] += 1
        
        return {
            'approved': approved,
            'direction': direction,
            'higher_tf_votes': higher_votes,
            'lower_tf_votes': lower_votes,
            'timeframes_detail': results,
            'required_higher': self.required_higher_tf,
            'required_lower': self.required_lower_tf
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
            return {
                'allowed': False,
                'reason': f"MTF: Sin alineación suficiente",
                'mtf_analysis': mtf_analysis
            }
        
        # Verificar dirección
        if signal_type == 1 and mtf_analysis['direction'] == 'buy':
            return {
                'allowed': True,
                'reason': f"MTF: ✅ BUY Aprobado",
                'mtf_analysis': mtf_analysis
            }
        elif signal_type == -1 and mtf_analysis['direction'] == 'sell':
            return {
                'allowed': True,
                'reason': f"MTF: ✅ SELL Aprobado",
                'mtf_analysis': mtf_analysis
            }
        else:
            direction_name = "BUY" if signal_type == 1 else "SELL"
            mtf_direction = mtf_analysis['direction'].upper()
            return {
                'allowed': False,
                'reason': f"MTF: ⛔ {direction_name} bloqueado (MTF indica {mtf_direction})",
                'mtf_analysis': mtf_analysis
            }
    
    def get_detailed_summary(self):
        """🆕 OPCIÓN C: Retorna resumen detallado de análisis MTF"""
        mtf_analysis = self.analyze_all_timeframes()
        
        summary_lines = []
        summary_lines.append("📊 ANÁLISIS MULTI-TIMEFRAME (OPCIÓN C - PRIORITARIO):")
        summary_lines.append("")
        
        # Timeframes SUPERIORES (Prioritarios)
        summary_lines.append("   🔴 TIMEFRAMES SUPERIORES (Prioritarios H4/D1/W1):")
        for tf_name in ['H4', 'D1', 'W1']:
            tf_data = mtf_analysis['timeframes_detail'][tf_name]
            bias = tf_data['bias']
            strength = tf_data['strength']
            
            emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(bias, "⚪")
            direction = bias.upper()[:4]
            
            summary_lines.append(f"      {tf_name}: {emoji} {direction} (Fuerza:{strength:.2f})")
        
        higher_votes = mtf_analysis['higher_tf_votes']
        summary_lines.append(f"      Votos: {higher_votes['bullish']}B / {higher_votes['bearish']}S / {higher_votes['neutral']}N (Req: {self.required_higher_tf})")
        summary_lines.append("")
        
        # Timeframes INFERIORES (Confirmación)
        summary_lines.append("   🔵 TIMEFRAMES INFERIORES (Confirmación M30/H1):")
        for tf_name in ['M30', 'H1']:
            tf_data = mtf_analysis['timeframes_detail'][tf_name]
            bias = tf_data['bias']
            strength = tf_data['strength']
            
            emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(bias, "⚪")
            direction = bias.upper()[:4]
            
            summary_lines.append(f"      {tf_name}: {emoji} {direction} (Fuerza:{strength:.2f})")
        
        lower_votes = mtf_analysis['lower_tf_votes']
        summary_lines.append(f"      Votos: {lower_votes['bullish']}B / {lower_votes['bearish']}S / {lower_votes['neutral']}N (Req: {self.required_lower_tf})")
        summary_lines.append("")
        
        summary_lines.append(f"   ────────────────────────────")
        
        if mtf_analysis['approved']:
            direction_emoji = "🟢" if mtf_analysis['direction'] == 'buy' else "🔴"
            direction_text = mtf_analysis['direction'].upper()
            
            # Convertir 'buy'/'sell' a 'bullish'/'bearish' para acceder al diccionario
            if mtf_analysis['direction'] == 'buy':
                bias_key = 'bullish'
            else:
                bias_key = 'bearish'
            
            summary_lines.append(f"   {direction_emoji} RESULTADO: {direction_text} APROBADO ✅")
            summary_lines.append(f"   📋 Regla cumplida: {higher_votes[bias_key]}/{self.required_higher_tf} superiores + {lower_votes[bias_key]}/{self.required_lower_tf} inferiores")
        else:
            summary_lines.append(f"   ⛔ RESULTADO: SIN ALINEACIÓN SUFICIENTE")
            summary_lines.append(f"   ⚠️ No se cumple la regla: {self.required_higher_tf} superiores + {self.required_lower_tf} inferiores")
        
        return "\n".join(summary_lines)
    
    def get_stats(self):
        """Retorna estadísticas del sistema MTF"""
        total = self.stats['operations_approved'] + self.stats['operations_blocked']
        approval_rate = (self.stats['operations_approved'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'approval_rate': approval_rate
        }
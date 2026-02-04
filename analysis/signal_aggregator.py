"""
╔══════════════════════════════════════════════════════════════════════════╗
║       AGREGADOR DE SEÑALES v6.0 - ML MTF + SIN COLA DE ESPERA          ║
║                                                                          ║
║  🆕 v6.0: ML con análisis multi-timeframe integrado                     ║
║  ✅ ML predice en M30, H1, H4 y genera consenso                         ║
║  ✅ Las señales bloqueadas por cooldown se DESCARTAN completamente      ║
║  ✅ Timeout de 2 minutos para señales antiguas                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from config import MAX_POSITIONS_PER_STRATEGY, QUALITY_FILTERS


class SignalAggregator:
    """
    Sistema de agregación con ML MTF
    
    🆕 v6.0: ML con análisis multi-timeframe
    - Recolecta señales de las 6 estrategias
    - ML ahora analiza M30, H1, H4
    - Cooldown global integrado
    """
    
    def __init__(self, ensemble, sr_system, fib_system, pa_system,
                 candlestick_system, liquidity_system, mtf_analyzer=None, 
                 global_cooldown=None, logger=None):
        self.ensemble = ensemble
        self.sr_system = sr_system
        self.fib_system = fib_system
        self.pa_system = pa_system
        self.candlestick_system = candlestick_system
        self.liquidity_system = liquidity_system
        self.mtf_analyzer = mtf_analyzer
        self.global_cooldown = global_cooldown
        self.logger = logger
        
        self.mtf_enabled = True
        self.signal_timeout_minutes = 2
        
        self.max_positions_per_strategy = MAX_POSITIONS_PER_STRATEGY
        self.quality_filters = QUALITY_FILTERS
        
        self.signals_history = []
        self.total_signals_detected = 0
        self.total_signals_executed = 0
        
        self.timeout_stats = {
            'signals_expired': 0,
            'signals_revalidated': 0,
            'revalidation_failed': 0,
            'revalidation_passed': 0
        }
        
        self.cooldown_stats = {
            'signals_blocked': 0,
            'signals_discarded': 0
        }
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def set_mtf_enabled(self, enabled):
        """Actualiza estado de MTF"""
        self.mtf_enabled = enabled
        if self.mtf_analyzer:
            if enabled:
                self.send_log(" ")
            else:
                self.send_log("⚠️ MTF ESTRICTO: Desactivado - Todas las señales permitidas")
    
    def is_signal_expired(self, signal):
        """Verifica si una señal ha expirado"""
        if 'timestamp' not in signal:
            return True
        
        signal_time = signal['timestamp']
        now = datetime.now()
        elapsed_minutes = (now - signal_time).total_seconds() / 60
        
        if elapsed_minutes > self.signal_timeout_minutes:
            return True
        
        return False
    
    def get_signal_age_seconds(self, signal):
        """Obtiene edad de la señal en segundos"""
        if 'timestamp' not in signal:
            return 999999
        
        signal_time = signal['timestamp']
        now = datetime.now()
        return (now - signal_time).total_seconds()
    
    def collect_all_signals(self, df, current_price, market_state, features):
        """
        Recolecta señales de TODAS las 6 estrategias
        🆕 v6.0: ML con análisis MTF
        """
        signals = []
        current_timestamp = datetime.now()
        
        # 1. SEÑAL ML CON MTF
        try:
            ml_signal_raw, confidence, mtf_details = self.ensemble.predict_with_mtf()
            
            if ml_signal_raw != 0:
                if confidence >= self.quality_filters['ml']['min_confidence']:
                    # Construir razón con info MTF
                    aligned_tfs = mtf_details.get('aligned_timeframes', [])
                    
                    if len(aligned_tfs) >= 2:
                        reason = f"ML MTF: {self.ensemble.active_model} ({'+'.join(aligned_tfs)}) {confidence*100:.1f}%"
                    else:
                        reason = f"ML: {self.ensemble.active_model} ({confidence*100:.1f}%)"
                    
                    ml_signal_data = {
                        'strategy': 'ml',
                        'signal': int(ml_signal_raw),
                        'confidence': confidence,
                        'reason': reason,
                        'sl_pips': 70,
                        'tp_pips': 140,
                        'priority': 1,
                        'timestamp': current_timestamp,
                        'generation_price': current_price,
                        'mtf_details': mtf_details
                    }
                    signals.append(ml_signal_data)
        except Exception as e:
            pass
        
        # 2-6. SEÑALES DE OTRAS ESTRATEGIAS
        if self.sr_system.enabled:
            sr_signal = self.sr_system.get_signal(df, current_price)
            if sr_signal and sr_signal['confidence'] >= self.quality_filters['sr']['min_confidence']:
                sr_signal['strategy'] = 'sr'
                sr_signal['priority'] = 2
                sr_signal['timestamp'] = current_timestamp
                sr_signal['generation_price'] = current_price
                signals.append(sr_signal)
        
        if self.fib_system.enabled:
            fib_signal = self.fib_system.get_signal(df, current_price)
            if fib_signal and fib_signal['confidence'] >= self.quality_filters['fibo']['min_confidence']:
                fib_signal['strategy'] = 'fibo'
                fib_signal['priority'] = 2
                fib_signal['timestamp'] = current_timestamp
                fib_signal['generation_price'] = current_price
                signals.append(fib_signal)
        
        if self.pa_system.enabled:
            pa_signal = self.pa_system.get_signal(df)
            if pa_signal and pa_signal['confidence'] >= self.quality_filters['price_action']['min_confidence']:
                pa_signal['strategy'] = 'price_action'
                pa_signal['priority'] = 3
                pa_signal['timestamp'] = current_timestamp
                pa_signal['generation_price'] = current_price
                signals.append(pa_signal)
        
        if self.candlestick_system.enabled:
            cs_signal = self.candlestick_system.get_signal(df)
            if cs_signal and cs_signal['confidence'] >= self.quality_filters['candlestick']['min_confidence']:
                cs_signal['strategy'] = 'candlestick'
                cs_signal['priority'] = 2
                cs_signal['timestamp'] = current_timestamp
                cs_signal['generation_price'] = current_price
                signals.append(cs_signal)
        
        if self.liquidity_system.enabled:
            liq_signal = self.liquidity_system.get_signal(df, current_price)
            if liq_signal and liq_signal['confidence'] >= self.quality_filters['liquidity']['min_confidence']:
                liq_signal['strategy'] = 'liquidity'
                liq_signal['priority'] = 1
                liq_signal['timestamp'] = current_timestamp
                liq_signal['generation_price'] = current_price
                signals.append(liq_signal)
        
        self.total_signals_detected += len(signals)
        return signals
    
    def revalidate_signal(self, signal, df, current_price, market_state, features):
        """RE-VALIDA una señal antes de ejecutarla"""
        self.timeout_stats['signals_revalidated'] += 1
        
        strategy = signal.get('strategy', 'unknown')
        original_signal = signal['signal']
        
        try:
            # Re-validar según estrategia
            if strategy == 'ml':
                # ML MTF re-validación
                ml_signal_raw, confidence, mtf_details = self.ensemble.predict_with_mtf()
                
                if ml_signal_raw != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, f"ML cambió predicción: {original_signal} → {ml_signal_raw}"
                
                if confidence < self.quality_filters['ml']['min_confidence']:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, f"ML confianza bajó: {signal['confidence']:.2f} → {confidence:.2f}"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, f"ML re-validado OK (conf: {confidence:.2f})"
            
            else:
                self.timeout_stats['revalidation_passed'] += 1
                return True, "Re-validado OK"
                
        except Exception as e:
            self.timeout_stats['revalidation_failed'] += 1
            return False, f"Error re-validando: {str(e)}"
    
    def filter_and_prioritize(self, signals, current_positions, active_trades_dict, max_total_positions=10):
        """
        Filtra señales con timeout, cooldown, MTF y límites
        """
        if not signals:
            return []
        
        # FILTRO 1: TIMEOUT
        valid_signals = []
        
        for signal in signals:
            if not self.is_signal_expired(signal):
                valid_signals.append(signal)
            else:
                self.timeout_stats['signals_expired'] += 1
        
        if len(signals) != len(valid_signals):
            expired_count = len(signals) - len(valid_signals)
            self.send_log(f"⏰ {expired_count} señal(es) descartadas por timeout ({self.signal_timeout_minutes} min)")
        
        signals = valid_signals
        
        if not signals:
            return []
        
        # FILTRO 2: COOLDOWN GLOBAL
        if self.global_cooldown:
            cooldown_passed_signals = []
            blocked_count = 0
            
            for signal in signals:
                strategy = signal.get('strategy', 'unknown')
                signal_dir = "BUY" if signal['signal'] == 1 else "SELL"
                
                can_operate, reason, time_remaining = self.global_cooldown.can_operate(strategy)
                
                if can_operate:
                    cooldown_passed_signals.append(signal)
                else:
                    blocked_count += 1
                    self.global_cooldown.block_operation(strategy, reason)
                    self.cooldown_stats['signals_blocked'] += 1
                    self.cooldown_stats['signals_discarded'] += 1
                    
                    if time_remaining >= 14.8:
                        self.send_log(f"⏱️ COOLDOWN: {strategy.upper()} {signal_dir} DESCARTADA - {reason}")
            
            if blocked_count > 0:
                strategies_blocked = set(s['strategy'] for s in signals if s not in cooldown_passed_signals)
                self.send_log(f"🚫 {blocked_count} señal(es) DESCARTADAS por cooldown (NO se guardan en cola)")
            
            signals = cooldown_passed_signals
        
        if not signals:
            return []
        
        # FILTRO 3: MTF
        if self.mtf_enabled and self.mtf_analyzer:
            mtf_analysis = self.mtf_analyzer.analyze_all_timeframes()
            mtf_approved = mtf_analysis.get('approved', False)
            mtf_direction = mtf_analysis.get('direction', None)
            
            mtf_filtered_signals = []
            
            for signal in signals:
                signal_type = signal['signal']
                strategy = signal.get('strategy', 'unknown')
                signal_direction_name = "BUY" if signal_type == 1 else "SELL"
                
                if mtf_approved and mtf_direction:
                    if mtf_direction == 'buy' and signal_type == 1:
                        signal['mtf_status'] = 'approved'
                        signal['mtf_reason'] = f"MTF: ✅ BUY Aprobado - {strategy.upper()} BUY alineado"
                        signal['mtf_analysis'] = mtf_analysis
                        mtf_filtered_signals.append(signal)
                    elif mtf_direction == 'sell' and signal_type == -1:
                        signal['mtf_status'] = 'approved'
                        signal['mtf_reason'] = f"MTF: ✅ SELL Aprobado - {strategy.upper()} SELL alineado"
                        signal['mtf_analysis'] = mtf_analysis
                        mtf_filtered_signals.append(signal)
                    else:
                        signal['mtf_status'] = 'blocked'
                        signal['mtf_reason'] = f"MTF: ⛔ {signal_direction_name} bloqueado"
                else:
                    signal['mtf_status'] = 'blocked'
                    signal['mtf_reason'] = f"MTF: ⛔ Sin alineación suficiente"
            
            if len(mtf_filtered_signals) < len(signals):
                blocked = len(signals) - len(mtf_filtered_signals)
                self.send_log(f"⛔ MTF bloqueó {blocked} señal(es)")
            
            signals = mtf_filtered_signals
        
        # FILTRO 4: LÍMITES POR ESTRATEGIA
        total_open = len(current_positions)
        if total_open >= max_total_positions:
            return []
        
        buy_signals = [s for s in signals if s['signal'] == 1]
        sell_signals = [s for s in signals if s['signal'] == -1]
        
        final_signals = []
        
        for signal in buy_signals + sell_signals:
            strategy = signal['strategy']
            
            active_count = sum(1 for trade_info in active_trades_dict.values() 
                            if trade_info.get('strategy') == strategy)
            
            max_allowed = self.max_positions_per_strategy.get(strategy, 2)
            
            if active_count < max_allowed:
                if total_open + len(final_signals) < max_total_positions:
                    signal['independent'] = True
                    signal['confirmed'] = False
                    final_signals.append(signal)
        
        final_signals.sort(key=lambda x: (x['priority'], -x['confidence']))
        
        available_slots = max_total_positions - total_open
        final_signals = final_signals[:available_slots]
        
        return final_signals
    
    def mark_signal_as_executed(self, signal):
        """Marca una señal como ejecutada y registra en cooldown"""
        strategy = signal.get('strategy', 'unknown')
        
        if self.global_cooldown:
            self.global_cooldown.register_operation(strategy)
        
        self.total_signals_executed += 1
    
    def get_stats(self):
        """Retorna estadísticas del agregador"""
        base_stats = {
            'total_signals_detected': self.total_signals_detected,
            'total_signals_executed': self.total_signals_executed,
            'execution_rate': (self.total_signals_executed / self.total_signals_detected * 100) if self.total_signals_detected > 0 else 0,
            'strategies_active': sum([
                1 if self.sr_system.enabled else 0,
                1 if self.fib_system.enabled else 0,
                1 if self.pa_system.enabled else 0,
                1 if self.candlestick_system.enabled else 0,
                1 if self.liquidity_system.enabled else 0,
                1
            ])
        }
        
        base_stats['timeout_stats'] = self.timeout_stats.copy()
        base_stats['cooldown_stats'] = self.cooldown_stats.copy()
        
        if self.global_cooldown:
            base_stats['global_cooldown_stats'] = self.global_cooldown.get_stats()
        
        return base_stats
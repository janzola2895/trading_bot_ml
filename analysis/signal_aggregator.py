"""
╔══════════════════════════════════════════════════════════════════════════╗
║       AGREGADOR DE SEÑALES v5.4.1 + COOLDOWN GLOBAL CORREGIDO           ║
║                                                                          ║
║  🔧 v5.4.1: FIX CRÍTICO - Registra operaciones en cooldown              ║
║  ✅ Cooldown independiente por estrategia (15-60 min)                   ║
║  ✅ Timeout reducido a 2 minutos (más estricto)                         ║
║  ✅ Re-validación antes de ejecutar                                     ║
║  ✅ AHORA SÍ registra cuando se ejecuta una operación                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from config import MAX_POSITIONS_PER_STRATEGY, QUALITY_FILTERS


class SignalAggregator:
    """
    ⭐ v5.4.1: Sistema con cooldown GLOBAL y registro correcto
    - Recolecta señales de las 6 estrategias
    - Aplica filtro MTF (bloquea señales no alineadas)
    - 🆕 COOLDOWN GLOBAL: Previene operaciones consecutivas
    - 🆕 TIMEOUT 2 MIN: Señales válidas por 2 minutos máximo
    - 🆕 RE-VALIDACIÓN: Verifica condiciones antes de ejecutar
    - 🔧 FIX: Registra operaciones correctamente en cooldown
    - Sistema de límites por estrategia
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
        self.global_cooldown = global_cooldown  # 🆕 Sistema global de cooldown
        self.logger = logger
        
        self.mtf_enabled = True
        
        # 🆕 TIMEOUT REDUCIDO A 2 MINUTOS
        self.signal_timeout_minutes = 2  # Más estricto
        
        # Límites individuales por estrategia
        self.max_positions_per_strategy = MAX_POSITIONS_PER_STRATEGY
        
        # Filtros de calidad individuales
        self.quality_filters = QUALITY_FILTERS
        
        self.signals_history = []
        self.total_signals_detected = 0
        self.total_signals_executed = 0
        
        # 🆕 Estadísticas de timeout
        self.timeout_stats = {
            'signals_expired': 0,
            'signals_revalidated': 0,
            'revalidation_failed': 0,
            'revalidation_passed': 0
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
                self.send_log("✅ MTF ESTRICTO: Activado - Solo señales alineadas")
            else:
                self.send_log("⚠️ MTF ESTRICTO: Desactivado - Todas las señales permitidas")
    
    def is_signal_expired(self, signal):
        """
        🆕 Verifica si una señal ha expirado por timeout (ahora 2 min)
        
        Args:
            signal: Señal a verificar
            
        Returns:
            bool: True si expiró, False si sigue válida
        """
        if 'timestamp' not in signal:
            # Señal antigua sin timestamp - considerarla expirada
            return True
        
        signal_time = signal['timestamp']
        now = datetime.now()
        
        elapsed_minutes = (now - signal_time).total_seconds() / 60
        
        if elapsed_minutes > self.signal_timeout_minutes:
            return True
        
        return False
    
    def get_signal_age_seconds(self, signal):
        """
        🆕 Obtiene edad de la señal en segundos
        
        Args:
            signal: Señal a verificar
            
        Returns:
            float: Edad en segundos
        """
        if 'timestamp' not in signal:
            return 999999  # Muy antigua
        
        signal_time = signal['timestamp']
        now = datetime.now()
        
        return (now - signal_time).total_seconds()
    
    def collect_all_signals(self, df, current_price, market_state, features):
        """
        Recolecta señales de TODAS las 6 estrategias
        🆕 AHORA AGREGA TIMESTAMP A CADA SEÑAL
        """
        signals = []
        current_timestamp = datetime.now()  # 🆕 Timestamp único para este ciclo
        
        # 1. SEÑAL ML
        try:
            import pandas as pd
            ml_signal_raw, probabilities = self.ensemble.predict_with_active_model(
                pd.DataFrame([features])
            )
            
            if ml_signal_raw != 0:
                confidence = float(max(probabilities))
                
                if confidence >= self.quality_filters['ml']['min_confidence']:
                    ml_signal_data = {
                        'strategy': 'ml',
                        'signal': int(ml_signal_raw),
                        'confidence': confidence,
                        'reason': f"ML: {self.ensemble.active_model} ({confidence*100:.1f}%)",
                        'sl_pips': 70,
                        'tp_pips': 140,
                        'priority': 1,
                        'timestamp': current_timestamp,  # 🆕 TIMESTAMP
                        'generation_price': current_price  # 🆕 Precio cuando se generó
                    }
                    signals.append(ml_signal_data)
        except Exception as e:
            pass
        
        # 2. SEÑAL SUPPORT/RESISTANCE
        if self.sr_system.enabled:
            sr_signal = self.sr_system.get_signal(df, current_price)
            if sr_signal and sr_signal['confidence'] >= self.quality_filters['sr']['min_confidence']:
                sr_signal['strategy'] = 'sr'
                sr_signal['priority'] = 2
                sr_signal['timestamp'] = current_timestamp  # 🆕
                sr_signal['generation_price'] = current_price  # 🆕
                signals.append(sr_signal)
        
        # 3. SEÑAL FIBONACCI
        if self.fib_system.enabled:
            fib_signal = self.fib_system.get_signal(df, current_price)
            if fib_signal and fib_signal['confidence'] >= self.quality_filters['fibo']['min_confidence']:
                fib_signal['strategy'] = 'fibo'
                fib_signal['priority'] = 2
                fib_signal['timestamp'] = current_timestamp  # 🆕
                fib_signal['generation_price'] = current_price  # 🆕
                signals.append(fib_signal)
        
        # 4. SEÑAL PRICE ACTION
        if self.pa_system.enabled:
            pa_signal = self.pa_system.get_signal(df)
            if pa_signal and pa_signal['confidence'] >= self.quality_filters['price_action']['min_confidence']:
                pa_signal['strategy'] = 'price_action'
                pa_signal['priority'] = 3
                pa_signal['timestamp'] = current_timestamp  # 🆕
                pa_signal['generation_price'] = current_price  # 🆕
                signals.append(pa_signal)
        
        # 5. SEÑAL CANDLESTICK PATTERNS
        if self.candlestick_system.enabled:
            cs_signal = self.candlestick_system.get_signal(df)
            if cs_signal and cs_signal['confidence'] >= self.quality_filters['candlestick']['min_confidence']:
                cs_signal['strategy'] = 'candlestick'
                cs_signal['priority'] = 2
                cs_signal['timestamp'] = current_timestamp  # 🆕
                cs_signal['generation_price'] = current_price  # 🆕
                signals.append(cs_signal)
        
        # 6. SEÑAL LIQUIDEZ
        if self.liquidity_system.enabled:
            liq_signal = self.liquidity_system.get_signal(df, current_price)
            if liq_signal and liq_signal['confidence'] >= self.quality_filters['liquidity']['min_confidence']:
                liq_signal['strategy'] = 'liquidity'
                liq_signal['priority'] = 1
                liq_signal['timestamp'] = current_timestamp  # 🆕
                liq_signal['generation_price'] = current_price  # 🆕
                signals.append(liq_signal)
        
        self.total_signals_detected += len(signals)
        return signals
    
    def revalidate_signal(self, signal, df, current_price, market_state, features):
        """
        🆕 RE-VALIDA una señal antes de ejecutarla
        
        Verifica si las condiciones que generaron la señal siguen siendo válidas
        
        Args:
            signal: Señal a re-validar
            df: DataFrame con datos actuales de mercado
            current_price: Precio actual
            market_state: Estado actual del mercado
            features: Features actuales para ML
            
        Returns:
            tuple: (is_valid: bool, reason: str)
        """
        self.timeout_stats['signals_revalidated'] += 1
        
        strategy = signal.get('strategy', 'unknown')
        original_signal = signal['signal']
        
        try:
            # Re-validar según estrategia
            if strategy == 'ml':
                import pandas as pd
                ml_signal_raw, probabilities = self.ensemble.predict_with_active_model(
                    pd.DataFrame([features])
                )
                
                if ml_signal_raw != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, f"ML cambió predicción: {original_signal} → {ml_signal_raw}"
                
                new_confidence = float(max(probabilities))
                if new_confidence < self.quality_filters['ml']['min_confidence']:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, f"ML confianza bajó: {signal['confidence']:.2f} → {new_confidence:.2f}"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, f"ML re-validado OK (conf: {new_confidence:.2f})"
            
            elif strategy == 'sr':
                sr_signal = self.sr_system.get_signal(df, current_price)
                
                if sr_signal is None:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "S/R: Nivel ya no es válido"
                
                if sr_signal['signal'] != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, f"S/R cambió dirección"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, "S/R re-validado OK"
            
            elif strategy == 'fibo':
                fib_signal = self.fib_system.get_signal(df, current_price)
                
                if fib_signal is None:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Fibo: Nivel ya no está cerca"
                
                if fib_signal['signal'] != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Fibo cambió dirección"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, "Fibo re-validado OK"
            
            elif strategy == 'price_action':
                pa_signal = self.pa_system.get_signal(df)
                
                if pa_signal is None:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "PA: Patrón ya no presente"
                
                if pa_signal['signal'] != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "PA cambió dirección"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, "PA re-validado OK"
            
            elif strategy == 'candlestick':
                cs_signal = self.candlestick_system.get_signal(df)
                
                if cs_signal is None:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Candlestick: Patrón ya no presente"
                
                if cs_signal['signal'] != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Candlestick cambió dirección"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, "Candlestick re-validado OK"
            
            elif strategy == 'liquidity':
                liq_signal = self.liquidity_system.get_signal(df, current_price)
                
                if liq_signal is None:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Liquidez: Zona ya no válida"
                
                if liq_signal['signal'] != original_signal:
                    self.timeout_stats['revalidation_failed'] += 1
                    return False, "Liquidez cambió dirección"
                
                self.timeout_stats['revalidation_passed'] += 1
                return True, "Liquidez re-validada OK"
            
            else:
                # Estrategia desconocida - rechazar
                self.timeout_stats['revalidation_failed'] += 1
                return False, f"Estrategia desconocida: {strategy}"
                
        except Exception as e:
            self.timeout_stats['revalidation_failed'] += 1
            return False, f"Error re-validando: {str(e)}"
    
    def filter_and_prioritize(self, signals, current_positions, active_trades_dict, max_total_positions=10):
        """
        🆕 v5.4.1: Filtra señales con:
        1. Timeout (2 min)
        2. MTF estricto
        3. 🆕 COOLDOWN GLOBAL por estrategia
        4. Límites por estrategia
        """
        if not signals:
            return []
        
        # ═══════════════════════════════════════════════════════════
        # FILTRO 1: ELIMINAR SEÑALES EXPIRADAS (TIMEOUT 2 MIN)
        # ═══════════════════════════════════════════════════════════
        valid_signals = []
        expired_signals = []
        
        for signal in signals:
            if self.is_signal_expired(signal):
                age_seconds = self.get_signal_age_seconds(signal)
                strategy = signal.get('strategy', 'unknown')
                signal_dir = "BUY" if signal['signal'] == 1 else "SELL"
                
                expired_signals.append(signal)
                self.timeout_stats['signals_expired'] += 1
                
                self.send_log(f"⏰ SEÑAL EXPIRADA: {strategy.upper()} {signal_dir} (Antigüedad: {age_seconds/60:.1f} min)")
            else:
                valid_signals.append(signal)
        
        if expired_signals:
            self.send_log(f"")
            self.send_log(f"⏰⏰⏰ DESCARTADAS {len(expired_signals)} SEÑAL(ES) POR TIMEOUT ⏰⏰⏰")
            for sig in expired_signals:
                age = self.get_signal_age_seconds(sig) / 60
                sig_dir = "BUY" if sig['signal'] == 1 else "SELL"
                self.send_log(f"   • {sig['strategy'].upper()} {sig_dir}: {age:.1f} min (máx: {self.signal_timeout_minutes} min)")
            self.send_log(f"")
        
        # Continuar con señales válidas
        signals = valid_signals
        
        if not signals:
            return []
        
        # ═══════════════════════════════════════════════════════════
        # FILTRO 2: 🆕 COOLDOWN GLOBAL POR ESTRATEGIA
        # ═══════════════════════════════════════════════════════════
        if self.global_cooldown:
            cooldown_passed_signals = []
            cooldown_blocked_signals = []
            
            for signal in signals:
                strategy = signal.get('strategy', 'unknown')
                signal_dir = "BUY" if signal['signal'] == 1 else "SELL"
                
                # Verificar cooldown
                can_operate, reason, time_remaining = self.global_cooldown.can_operate(strategy)
                
                if can_operate:
                    cooldown_passed_signals.append(signal)
                else:
                    cooldown_blocked_signals.append(signal)
                    self.global_cooldown.block_operation(strategy, reason)
                    self.send_log(f"⏱️ COOLDOWN BLOQUEÓ: {strategy.upper()} {signal_dir} - {reason}")
            
            if cooldown_blocked_signals:
                self.send_log(f"")
                self.send_log(f"⏱️⏱️⏱️ COOLDOWN BLOQUEÓ {len(cooldown_blocked_signals)} SEÑAL(ES) ⏱️⏱️⏱️")
                for sig in cooldown_blocked_signals:
                    strategy = sig['strategy']
                    sig_dir = "BUY" if sig['signal'] == 1 else "SELL"
                    _, reason, time_rem = self.global_cooldown.can_operate(strategy)
                    self.send_log(f"   • {strategy.upper()} {sig_dir}: {reason}")
                self.send_log(f"")
            
            signals = cooldown_passed_signals
        
        if not signals:
            return []
        
        # ═══════════════════════════════════════════════════════════
        # FILTRO 3: MULTI-TIMEFRAME ESTRICTO
        # ═══════════════════════════════════════════════════════════
        if self.mtf_enabled and self.mtf_analyzer:
            # Obtener análisis MTF actual
            mtf_analysis = self.mtf_analyzer.analyze_all_timeframes()
            mtf_approved = mtf_analysis.get('approved', False)
            mtf_direction = mtf_analysis.get('direction', None)
            
            mtf_filtered_signals = []
            blocked_signals = []
            
            for signal in signals:
                signal_type = signal['signal']  # 1=BUY, -1=SELL
                strategy = signal.get('strategy', 'unknown')
                signal_direction_name = "BUY" if signal_type == 1 else "SELL"
                
                # VALIDACIÓN ESTRICTA MTF
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
                        signal['mtf_reason'] = f"MTF: ⛔ {signal_direction_name} bloqueado - MTF aprueba solo {mtf_direction.upper()}"
                        signal['mtf_analysis'] = mtf_analysis
                        blocked_signals.append(signal)
                        
                else:
                    signal['mtf_status'] = 'blocked'
                    signal['mtf_reason'] = f"MTF: ⛔ Sin alineación suficiente para {signal_direction_name}"
                    signal['mtf_analysis'] = mtf_analysis
                    blocked_signals.append(signal)
            
            if blocked_signals:
                self.send_log("")
                self.send_log(f"⛔⛔⛔ MTF BLOQUEÓ {len(blocked_signals)} SEÑAL(ES) ⛔⛔⛔")
                for sig in blocked_signals:
                    sig_dir = "BUY" if sig['signal'] == 1 else "SELL"
                    self.send_log(f"   • {sig['strategy'].upper()} {sig_dir}: {sig['mtf_reason']}")
                self.send_log("")
            
            if mtf_filtered_signals:
                self.send_log(f"✅ MTF APROBÓ {len(mtf_filtered_signals)} señal(es)")
            
            signals = mtf_filtered_signals
        
        # ═══════════════════════════════════════════════════════════
        # FILTRO 4: LÍMITES POR ESTRATEGIA Y PRIORIZACIÓN
        # ═══════════════════════════════════════════════════════════
        
        # Verificar límite total
        total_open = len(current_positions)
        if total_open >= max_total_positions:
            return []
        
        # Separar por dirección
        buy_signals = [s for s in signals if s['signal'] == 1]
        sell_signals = [s for s in signals if s['signal'] == -1]
        
        final_signals = []
        
        # PROCESAR SEÑALES DE COMPRA
        for signal in buy_signals:
            strategy = signal['strategy']
            
            active_count = sum(1 for trade_info in active_trades_dict.values() 
                            if trade_info.get('strategy') == strategy)
            
            max_allowed = self.max_positions_per_strategy.get(strategy, 2)
            
            if active_count < max_allowed:
                if total_open + len(final_signals) < max_total_positions:
                    signal['independent'] = True
                    signal['confirmed'] = False
                    final_signals.append(signal)
        
        # PROCESAR SEÑALES DE VENTA
        for signal in sell_signals:
            if total_open + len(final_signals) >= max_total_positions:
                break
            
            strategy = signal['strategy']
            
            active_count = sum(1 for trade_info in active_trades_dict.values() 
                            if trade_info.get('strategy') == strategy)
            
            max_allowed = self.max_positions_per_strategy.get(strategy, 2)
            
            if active_count < max_allowed:
                if total_open + len(final_signals) < max_total_positions:
                    signal['independent'] = True
                    signal['confirmed'] = False
                    final_signals.append(signal)
        
        # ORDENAR POR PRIORIDAD Y CONFIANZA
        final_signals.sort(key=lambda x: (x['priority'], -x['confidence']))
        
        # Limitar a no superar max_total_positions
        available_slots = max_total_positions - total_open
        final_signals = final_signals[:available_slots]
        
        return final_signals
    
    def mark_signal_as_executed(self, signal):
        """
        🔧 NUEVO v5.4.1: Marca una señal como ejecutada y registra en cooldown
        
        CRÍTICO: Este método DEBE ser llamado DESPUÉS de ejecutar una operación
        
        Args:
            signal: Señal que fue ejecutada
        """
        strategy = signal.get('strategy', 'unknown')
        
        # 🔧 REGISTRAR EN COOLDOWN GLOBAL
        if self.global_cooldown:
            self.global_cooldown.register_operation(strategy)
        
        # Actualizar estadísticas
        self.total_signals_executed += 1
    
    def get_stats(self):
        """Retorna estadísticas del agregador incluyendo timeout"""
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
                1  # ML siempre activo
            ])
        }
        
        # 🆕 Agregar estadísticas de timeout
        base_stats['timeout_stats'] = self.timeout_stats.copy()
        
        # 🆕 Agregar estadísticas de cooldown global
        if self.global_cooldown:
            base_stats['cooldown_stats'] = self.global_cooldown.get_stats()
        
        return base_stats
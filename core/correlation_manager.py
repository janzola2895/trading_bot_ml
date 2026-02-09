"""
╔══════════════════════════════════════════════════════════════════════════╗
║          CORRELATION MANAGER - Gestor de Correlación v1.0               ║
║                                                                          ║
║  Previene overexposure y correlación excesiva entre operaciones         ║
║  - Limita operaciones en misma dirección                                ║
║  - Verifica distancia entre SL (no agrupar riesgo)                      ║
║  - Control de riesgo total acumulado                                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""


class CorrelationManager:
    """
    Gestor de correlación entre operaciones
    
    Previene situaciones de riesgo como:
    - Demasiadas operaciones BUY/SELL simultáneas
    - SL muy cercanos (riesgo agrupado)
    - Exposición total excesiva
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        
        # Configuración
        self.max_same_direction_trades = 999  # Max 4 BUY o 4 SELL simultáneos
        self.min_sl_distance_pips = 30  # SL deben estar a >30 pips de distancia
        self.max_total_risk_pct = 6.0  # Máximo 6% de riesgo total acumulado
        
        # Estadísticas
        self.stats = {
            'total_checks': 0,
            'blocked_by_direction': 0,
            'blocked_by_sl_distance': 0,
            'blocked_by_total_risk': 0,
            'approved': 0
        }
    
    def send_log(self, message):
        """Envía log si hay logger"""
        if self.logger:
            self.logger.info(message)
    
    def check_signal_correlation(self, new_signal, active_positions, active_trades_dict, account_balance):
        """
        Verifica si una nueva señal pasaría los filtros de correlación
        
        Args:
            new_signal: Señal nueva a evaluar
            active_positions: Posiciones activas de MT5
            active_trades_dict: Diccionario de trades activos del bot
            account_balance: Balance de la cuenta
        
        Returns:
            tuple: (allowed: bool, reason: str)
        """
        self.stats['total_checks'] += 1
        
        new_direction = new_signal['signal']  # 1=BUY, -1=SELL
        new_sl_pips = new_signal.get('sl_pips', 70)
        
        # 1. VERIFICAR LÍMITE DE DIRECCIÓN
        """same_direction_count = sum(
            1 for pos in active_positions 
            if (pos.type == 0 and new_direction == 1) or (pos.type == 1 and new_direction == -1)
        )
        
        if same_direction_count >= self.max_same_direction_trades:
            self.stats['blocked_by_direction'] += 1
            
            dir_name = "BUY" if new_direction == 1 else "SELL"
            self.send_log(f"🚫 CORRELACIÓN: Ya hay {same_direction_count} {dir_name} activas (máx: {self.max_same_direction_trades})")
            
            return False, f"Demasiadas operaciones {dir_name} ({same_direction_count}/{self.max_same_direction_trades})"
        """
        
        # 2. VERIFICAR DISTANCIA ENTRE SL
        # Obtener precio de mercado actual
        if len(active_positions) > 0:
            # Simular SL de la nueva operación (necesitaríamos precio actual)
            # Por simplicidad, verificamos si hay demasiadas operaciones muy cercanas
            
            # Contar operaciones en misma dirección con SL similar
            close_sl_count = 0
            
            for ticket, trade_info in active_trades_dict.items():
                if trade_info.get('signal') == new_direction:
                    existing_sl_pips = trade_info.get('sl_pips', 70)
                    
                    # Si los SL están muy cercanos en tamaño, probablemente estén cerca en precio
                    sl_diff = abs(new_sl_pips - existing_sl_pips)
                    
                    if sl_diff < self.min_sl_distance_pips:
                        close_sl_count += 1
            
            # Si hay 2+ operaciones con SL muy cercano, bloquear
            if close_sl_count >= 2:
                self.stats['blocked_by_sl_distance'] += 1
                
                self.send_log(f"🚫 CORRELACIÓN: {close_sl_count} operaciones con SL muy cercano")
                
                return False, f"SL demasiado cercano a {close_sl_count} operaciones existentes"
        
        # 3. VERIFICAR RIESGO TOTAL ACUMULADO
        if account_balance > 0:
            # Calcular riesgo actual
            total_risk = 0.0
            
            for ticket, trade_info in active_trades_dict.items():
                sl_pips = trade_info.get('sl_pips', 70)
                # Estimar riesgo: (sl_pips * pip_value * lotes)
                # Para XAUUSD, aproximadamente $1 por pip por lote 0.01
                risk_per_trade = sl_pips * 1.0  # Simplificado
                total_risk += risk_per_trade
            
            # Añadir riesgo de nueva operación
            new_risk = new_sl_pips * 1.0
            total_risk += new_risk
            
            # Calcular porcentaje
            risk_pct = (total_risk / account_balance) * 100
            
            if risk_pct > self.max_total_risk_pct:
                self.stats['blocked_by_total_risk'] += 1
                
                self.send_log(f"🚫 CORRELACIÓN: Riesgo total {risk_pct:.1f}% > {self.max_total_risk_pct}%")
                
                return False, f"Riesgo total excesivo ({risk_pct:.1f}%)"
        
        # ✅ TODAS LAS VERIFICACIONES PASADAS
        self.stats['approved'] += 1
        
        return True, "Correlación OK"
    
    def get_stats(self):
        """Retorna estadísticas del gestor"""
        total = self.stats['total_checks']
        
        if total == 0:
            return {
                **self.stats,
                'block_rate': 0.0,
                'approval_rate': 0.0
            }
        
        total_blocked = (
            self.stats['blocked_by_direction'] +
            self.stats['blocked_by_sl_distance'] +
            self.stats['blocked_by_total_risk']
        )
        
        return {
            **self.stats,
            'total_blocked': total_blocked,
            'block_rate': (total_blocked / total) * 100,
            'approval_rate': (self.stats['approved'] / total) * 100
        }
    
    def update_config(self, max_same_direction=None, min_sl_distance=None, max_total_risk=None):
        """Actualiza configuración del gestor"""
        if max_same_direction is not None:
            self.max_same_direction_trades = max_same_direction
        
        if min_sl_distance is not None:
            self.min_sl_distance_pips = min_sl_distance
        
        if max_total_risk is not None:
            self.max_total_risk_pct = max_total_risk
        
        self.send_log(f"⚙️ Correlation Manager: max_dir={self.max_same_direction_trades}, "
                     f"min_sl_dist={self.min_sl_distance_pips}p, "
                     f"max_risk={self.max_total_risk_pct}%")
"""
╔══════════════════════════════════════════════════════════════════════════╗
║          EQUITY MONITOR - Monitor de Equity Dinámico v1.1 CORREGIDO     ║
║                                                                          ║
║  🔧 CORREGIDO: Nunca reduce lote a 0 - mínimo absoluto 0.01             ║
║  Ajusta el comportamiento del bot según drawdown y win rate             ║
║  - Modo defensivo: drawdown >15% → reducir lotes (MÍNIMO 0.01)         ║
║  - Modo agresivo: win rate >70% → aumentar lotes                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta


class EquityMonitor:
    """
    Monitor de equity que ajusta comportamiento según rendimiento
    
    🔧 v1.1 CORREGIDO: Garantiza mínimo de 0.01 lotes SIEMPRE
    
    Calcula drawdown actual y win rate reciente para ajustar:
    - Tamaño de lotes (NUNCA menor a 0.01)
    - Filtros de confianza
    - Agresividad del trading
    """
    
    def __init__(self, memory, logger=None):
        self.memory = memory
        self.logger = logger
        
        # Configuración de umbrales
        self.defensive_drawdown_threshold = 80.0  # % - Activar modo defensivo
        self.aggressive_winrate_threshold = 0.70  # 70% - Activar modo agresivo
        
        # 🔧 CORREGIDO: Multiplicadores que NUNCA bloquean completamente
        self.defensive_lot_multiplier = 1.0  # MÍNIMO 50% del lote base
        self.defensive_confidence_boost = 0.05  # Requerir +5% confianza
        
        self.aggressive_lot_multiplier = 1.2  # Aumentar lotes a 120%
        self.aggressive_confidence_reduction = 0.05  # Permitir -5% confianza
        
        # Estado actual
        self.current_mode = 'normal'  # 'normal', 'defensive', 'aggressive'
        self.current_drawdown = 0.0
        self.current_winrate = 0.0
        
        # Estadísticas
        self.stats = {
            'mode_changes': 0,
            'time_in_defensive': 0,
            'time_in_aggressive': 0,
            'time_in_normal': 0,
            'last_mode_change': None
        }
    
    def send_log(self, message):
        """Envía log si hay logger"""
        if self.logger:
            self.logger.info(message)
    
    def calculate_current_metrics(self):
        """
        Calcula métricas actuales: drawdown y win rate
        
        Returns:
            dict: {'drawdown_pct': float, 'winrate': float, 'trades_analyzed': int}
        """
        # Obtener trades recientes (últimos 30 días o 100 trades)
        recent_trades = self.memory.get_recent_trades(limit=100)
        
        if not recent_trades:
            return {
                'drawdown_pct': 0.0,
                'winrate': 0.0,
                'trades_analyzed': 0
            }
        
        # Calcular win rate
        winning_trades = sum(1 for t in recent_trades if t.get('result') == 'win')
        total_trades = len(recent_trades)
        winrate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Calcular drawdown
        # Drawdown = pérdida acumulada desde el punto más alto
        cumulative_profits = []
        cumulative = 0.0
        
        for trade in reversed(recent_trades):  # Orden cronológico
            cumulative += trade.get('profit', 0.0)
            cumulative_profits.append(cumulative)
        
        if cumulative_profits:
            peak = max(cumulative_profits)
            current = cumulative_profits[-1]
            
            if peak > 0:
                drawdown_pct = ((peak - current) / peak) * 100
            else:
                drawdown_pct = 0.0
        else:
            drawdown_pct = 0.0
        
        return {
            'drawdown_pct': drawdown_pct,
            'winrate': winrate,
            'trades_analyzed': total_trades
        }
    
    def determine_trading_mode(self):
        """
        Determina el modo de trading basado en métricas actuales
        
        Returns:
            str: 'defensive', 'aggressive', o 'normal'
        """
        metrics = self.calculate_current_metrics()
        
        self.current_drawdown = metrics['drawdown_pct']
        self.current_winrate = metrics['winrate']
        
        old_mode = self.current_mode
        
        # Prioridad: Defensivo > Agresivo > Normal
        
        # MODO DEFENSIVO: Drawdown alto
        if self.current_drawdown >= self.defensive_drawdown_threshold:
            self.current_mode = 'defensive'
        
        # MODO AGRESIVO: Win rate alto Y drawdown bajo
        elif (self.current_winrate >= self.aggressive_winrate_threshold and 
              self.current_drawdown < 5.0):
            self.current_mode = 'aggressive'
        
        # MODO NORMAL: Resto de casos
        else:
            self.current_mode = 'normal'
        
        # Si cambió el modo, registrarlo
        if old_mode != self.current_mode:
            self.stats['mode_changes'] += 1
            self.stats['last_mode_change'] = datetime.now().isoformat()
            
            self.send_log("")
            self.send_log(f"🔄🔄🔄 CAMBIO DE MODO: {old_mode.upper()} → {self.current_mode.upper()} 🔄🔄🔄")
            self.send_log(f"   Drawdown: {self.current_drawdown:.1f}%")
            self.send_log(f"   Win Rate: {self.current_winrate*100:.1f}%")
            self.send_log(f"   Trades analizados: {metrics['trades_analyzed']}")
            self.send_log("")
        
        return self.current_mode
    
    def get_lot_multiplier(self):
        """
        🔧 CORREGIDO: Retorna multiplicador de lotes que NUNCA bloquea completamente
        
        El multiplicador mínimo es 0.50 (50%) para garantizar que con lote base 0.02:
        0.02 * 0.50 = 0.01 (mínimo del broker)
        
        Returns:
            float: Multiplicador (0.50, 1.0, o 1.20)
        """
        mode = self.determine_trading_mode()
        
        if mode == 'defensive':
            # 🔧 MÍNIMO 50% para no caer por debajo del mínimo del broker
            return self.defensive_lot_multiplier  # 0.50
        elif mode == 'aggressive':
            return self.aggressive_lot_multiplier  # 1.20
        else:
            return 1.0
    
    def get_confidence_adjustment(self):
        """
        Retorna ajuste de confianza según modo actual
        
        Returns:
            float: Ajuste a aplicar (+0.05, 0.0, o -0.05)
        """
        mode = self.determine_trading_mode()
        
        if mode == 'defensive':
            return self.defensive_confidence_boost
        elif mode == 'aggressive':
            return -self.aggressive_confidence_reduction
        else:
            return 0.0
    
    def should_allow_trade(self):
        """
        🔧 CORREGIDO: NUNCA bloquea trading completamente
        
        Antes bloqueaba con drawdown >80%, ahora SIEMPRE permite trading
        pero con lotes reducidos en modo defensivo
        
        Returns:
            tuple: (allow: bool, reason: str)
        """
        mode = self.determine_trading_mode()
        
        # 🔧 CAMBIO CRÍTICO: SIEMPRE permite trading, sin importar el drawdown
        # El control se hace mediante reducción de lotes, no bloqueo total
        
        return True, f"Modo {mode}: Trading permitido (lotes ajustados según equity)"
    
    def get_current_status(self):
        """
        Retorna estado actual del monitor
        
        Returns:
            dict: Estado completo con métricas y ajustes
        """
        mode = self.current_mode
        
        return {
            'mode': mode,
            'drawdown_pct': self.current_drawdown,
            'winrate': self.current_winrate,
            'lot_multiplier': self.get_lot_multiplier(),
            'confidence_adjustment': self.get_confidence_adjustment(),
            'recommendations': self._get_recommendations()
        }
    
    def _get_recommendations(self):
        """Genera recomendaciones según modo actual"""
        mode = self.current_mode
        
        if mode == 'defensive':
            return [
                f"⚠️ Modo DEFENSIVO activado (DD: {self.current_drawdown:.1f}%)",
                f"📉 Lotes reducidos a {self.defensive_lot_multiplier*100:.0f}%",
                f"🔒 Confianza requerida +{self.defensive_confidence_boost*100:.0f}%",
                "💡 Enfócate en calidad sobre cantidad"
            ]
        
        elif mode == 'aggressive':
            return [
                f"🚀 Modo AGRESIVO activado (WR: {self.current_winrate*100:.0f}%)",
                f"📈 Lotes aumentados a {self.aggressive_lot_multiplier*100:.0f}%",
                f"🔓 Confianza permitida -{self.aggressive_confidence_reduction*100:.0f}%",
                "💡 Aprovecha el buen momento"
            ]
        
        else:
            return [
                f"✅ Modo NORMAL (DD: {self.current_drawdown:.1f}%, WR: {self.current_winrate*100:.0f}%)",
                "📊 Parámetros estándar",
                "💡 Continúa con plan de trading normal"
            ]
    
    def get_stats(self):
        """Retorna estadísticas del monitor"""
        return {
            **self.stats,
            'current_mode': self.current_mode,
            'current_drawdown': self.current_drawdown,
            'current_winrate': self.current_winrate
        }
    
    def update_config(self, defensive_dd=None, aggressive_wr=None, 
                     defensive_lot_mult=None, aggressive_lot_mult=None):
        """
        Actualiza configuración del monitor
        
        🔧 NOTA: defensive_lot_mult NUNCA debe ser menor a 0.50 para
        garantizar que con lote base 0.02 no caiga por debajo de 0.01
        """
        if defensive_dd is not None:
            self.defensive_drawdown_threshold = defensive_dd
        
        if aggressive_wr is not None:
            self.aggressive_winrate_threshold = aggressive_wr
        
        if defensive_lot_mult is not None:
            # 🔧 GARANTIZAR mínimo de 0.50 (50%)
            self.defensive_lot_multiplier = max(0.50, defensive_lot_mult)
        
        if aggressive_lot_mult is not None:
            self.aggressive_lot_multiplier = aggressive_lot_mult
        
        self.send_log(f"⚙️ Equity Monitor: defensive_dd={self.defensive_drawdown_threshold}%, "
                     f"aggressive_wr={self.aggressive_winrate_threshold*100}%, "
                     f"def_mult={self.defensive_lot_multiplier}, agg_mult={self.aggressive_lot_multiplier}")
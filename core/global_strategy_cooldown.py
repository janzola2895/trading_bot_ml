"""
╔══════════════════════════════════════════════════════════════════════════╗
║          COOLDOWN GLOBAL POR ESTRATEGIA v1.0 - NUEVO                     ║
║                                                                          ║
║  Sistema centralizado que previene operaciones consecutivas              ║
║  - Un cooldown por estrategia independiente                             ║
║  - Verifica ANTES de ejecutar señales                                   ║
║  - Configuración personalizada por estrategia                           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta


class GlobalStrategyCooldown:
    """
    Sistema GLOBAL de cooldown para prevenir operaciones consecutivas
    
    GARANTIZA que cada estrategia respete un tiempo mínimo entre operaciones:
    - ML: 15 minutos (operaciones frecuentes pero controladas)
    - S/R: 20 minutos (niveles cambian lentamente)
    - Fibonacci: 30 minutos (niveles muy estables)
    - Price Action: 20 minutos (patrones ocasionales)
    - Candlestick: 60 minutos (patrones de reversión espaciados)
    - Liquidez: 30 minutos (zonas tardan en revalidarse)
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        
        # ⏱️ COOLDOWNS POR ESTRATEGIA (en minutos)
        self.strategy_cooldowns = {
            'ml': 15,             # ML puede operar más frecuentemente
            'sr': 20,             # S/R necesita tiempo para confirmar
            'fibo': 30,           # Fibonacci muy espaciado
            'price_action': 20,   # PA patrones ocasionales
            'candlestick': 60,    # Candlestick MUY espaciado
            'liquidity': 30       # Liquidez necesita tiempo
        }
        
        # 📊 Tracking de última operación por estrategia
        self.last_operation_time = {
            'ml': None,
            'sr': None,
            'fibo': None,
            'price_action': None,
            'candlestick': None,
            'liquidity': None
        }
        
        # 📈 Estadísticas
        self.stats = {
            'ml': {'allowed': 0, 'blocked': 0},
            'sr': {'allowed': 0, 'blocked': 0},
            'fibo': {'allowed': 0, 'blocked': 0},
            'price_action': {'allowed': 0, 'blocked': 0},
            'candlestick': {'allowed': 0, 'blocked': 0},
            'liquidity': {'allowed': 0, 'blocked': 0}
        }
    
    def send_log(self, message):
        """Envía log si hay logger"""
        if self.logger:
            self.logger.info(message)
    
    def can_operate(self, strategy):
        """
        Verifica si una estrategia PUEDE operar (no está en cooldown)
        
        Args:
            strategy: Nombre de la estrategia ('ml', 'sr', etc.)
            
        Returns:
            tuple: (can_operate: bool, reason: str, time_remaining: float)
        """
        if strategy not in self.strategy_cooldowns:
            return True, "Estrategia desconocida - permitir", 0
        
        # Obtener última operación
        last_time = self.last_operation_time[strategy]
        
        # Si nunca operó, permitir
        if last_time is None:
            return True, "Primera operación", 0
        
        # Calcular tiempo transcurrido
        now = datetime.now()
        elapsed_minutes = (now - last_time).total_seconds() / 60
        
        # Obtener cooldown requerido
        required_cooldown = self.strategy_cooldowns[strategy]
        
        # Verificar si pasó el cooldown
        if elapsed_minutes >= required_cooldown:
            return True, f"Cooldown completado ({elapsed_minutes:.1f} min)", 0
        
        # En cooldown - calcular tiempo restante
        time_remaining = required_cooldown - elapsed_minutes
        
        return False, f"En cooldown: {time_remaining:.1f} min restantes", time_remaining
    
    def register_operation(self, strategy):
        """
        Registra que una estrategia ejecutó una operación
        
        Args:
            strategy: Nombre de la estrategia
        """
        if strategy not in self.last_operation_time:
            self.send_log(f"⚠️ Estrategia desconocida: {strategy}")
            return
        
        # Actualizar timestamp
        self.last_operation_time[strategy] = datetime.now()
        
        # Actualizar estadísticas
        self.stats[strategy]['allowed'] += 1
        
        # Log informativo
        cooldown = self.strategy_cooldowns[strategy]
        self.send_log(f"⏱️ COOLDOWN: {strategy.upper()} operó - Próxima en {cooldown} min")
    
    def block_operation(self, strategy, reason):
        """
        Registra que una operación fue bloqueada
        
        Args:
            strategy: Nombre de la estrategia
            reason: Razón del bloqueo
        """
        if strategy in self.stats:
            self.stats[strategy]['blocked'] += 1
    
    def get_strategy_status(self, strategy):
        """
        Obtiene estado actual de una estrategia
        
        Returns:
            dict: Estado completo con cooldown info
        """
        can_op, reason, time_rem = self.can_operate(strategy)
        
        last_time = self.last_operation_time[strategy]
        time_since_last = None
        
        if last_time:
            time_since_last = (datetime.now() - last_time).total_seconds() / 60
        
        return {
            'strategy': strategy,
            'can_operate': can_op,
            'reason': reason,
            'time_remaining': time_rem,
            'cooldown_minutes': self.strategy_cooldowns[strategy],
            'last_operation': last_time.isoformat() if last_time else None,
            'time_since_last': time_since_last,
            'stats': self.stats[strategy]
        }
    
    def get_all_status(self):
        """Retorna estado de TODAS las estrategias"""
        return {
            strategy: self.get_strategy_status(strategy)
            for strategy in self.strategy_cooldowns.keys()
        }
    
    def get_stats(self):
        """Retorna estadísticas globales"""
        total_allowed = sum(s['allowed'] for s in self.stats.values())
        total_blocked = sum(s['blocked'] for s in self.stats.values())
        total_checks = total_allowed + total_blocked
        
        block_rate = (total_blocked / total_checks * 100) if total_checks > 0 else 0
        
        return {
            'total_allowed': total_allowed,
            'total_blocked': total_blocked,
            'total_checks': total_checks,
            'block_rate': block_rate,
            'by_strategy': self.stats
        }
    
    def update_cooldown(self, strategy, new_cooldown_minutes):
        """
        Actualiza el cooldown de una estrategia
        
        Args:
            strategy: Nombre de la estrategia
            new_cooldown_minutes: Nuevo cooldown en minutos
        """
        if strategy in self.strategy_cooldowns:
            old_cooldown = self.strategy_cooldowns[strategy]
            self.strategy_cooldowns[strategy] = new_cooldown_minutes
            
            self.send_log(f"⚙️ Cooldown {strategy.upper()}: {old_cooldown} → {new_cooldown_minutes} min")
    
    def reset_strategy(self, strategy):
        """
        Resetea el cooldown de una estrategia específica
        
        Args:
            strategy: Nombre de la estrategia a resetear
        """
        if strategy in self.last_operation_time:
            self.last_operation_time[strategy] = None
            self.send_log(f"🔄 Cooldown {strategy.upper()} reseteado")
    
    def reset_all(self):
        """Resetea TODOS los cooldowns"""
        for strategy in self.last_operation_time.keys():
            self.last_operation_time[strategy] = None
        
        self.send_log("🔄 TODOS los cooldowns reseteados")
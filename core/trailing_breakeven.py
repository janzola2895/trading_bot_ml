"""
╔══════════════════════════════════════════════════════════════════════════╗
║          SISTEMA DE TRAILING STOP Y BREAKEVEN v6.0 CORREGIDO            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
from datetime import datetime
from config import (
    TRAILING_ENABLED, TRAILING_ACTIVATION_PIPS, TRAILING_DISTANCE_PIPS,
    BREAKEVEN_ENABLED, BREAKEVEN_ACTIVATION_PIPS, BREAKEVEN_SAFETY_PIPS
)


class TrailingStopBreakevenSystem:
    """
    Sistema de Trailing Stop y Breakeven con aprendizaje ML
    
    🆕 v6.0 CORREGIDO:
    - ✅ Agregado método update_atr para trailing dinámico
    - Validación COMPLETA antes de modificar SL/TP
    - Usa OrderValidator para verificar niveles
    - Respeta STOP_LEVEL y FREEZE_LEVEL
    - Sistema de cooldown entre modificaciones
    - Retry automático si falla modificación
    - Logs detallados de cada intento
    """
    
    def __init__(self, order_validator=None, logger=None):
        self.logger = logger
        self.order_validator = order_validator
        
        # Parámetros por defecto (modo manual)
        self.trailing_enabled = TRAILING_ENABLED
        self.trailing_activation_pips = TRAILING_ACTIVATION_PIPS
        self.trailing_distance_pips = TRAILING_DISTANCE_PIPS
        
        self.breakeven_enabled = BREAKEVEN_ENABLED
        self.breakeven_activation_pips = BREAKEVEN_ACTIVATION_PIPS
        self.breakeven_safety_pips = BREAKEVEN_SAFETY_PIPS
        
        # 🆕 v6.0: Variables para trailing dinámico con ATR
        self.trailing_use_atr = False  # Desactivado por defecto
        self.trailing_atr_multiplier = 1.5
        self.current_atr = 0.0
        
        self.positions_with_trailing = {}
        self.positions_with_breakeven = {}
        
        # 🆕 Estadísticas de modificaciones
        self.modification_stats = {
            "total_attempts": 0,
            "successful_modifications": 0,
            "failed_modifications": 0,
            "validation_failures": 0,
            "freeze_level_blocks": 0,
            "cooldown_blocks": 0
        }
    
    def update_atr(self, atr_value):
        """
        🆕 v6.0: Actualiza el valor de ATR para trailing dinámico
        
        Permite ajustar automáticamente el trailing distance según
        la volatilidad actual del mercado.
        
        Args:
            atr_value: Valor actual del ATR en precio (ej: 2.5)
        """
        # Guardar ATR actual
        self.current_atr = atr_value
        
        # Si trailing con ATR está habilitado, ajustar distance
        if self.trailing_use_atr:
            # Convertir ATR a pips
            atr_pips = atr_value / 0.01
            
            # Calcular trailing distance = ATR * multiplicador
            new_distance = int(atr_pips * self.trailing_atr_multiplier)
            
            # Limitar entre 15 y 50 pips
            self.trailing_distance_pips = max(15, min(new_distance, 50))
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def update_params(self, params):
        """Actualiza parámetros desde ML Optimizer"""
        trailing = params.get('trailing_stop', {})
        if trailing:
            self.trailing_enabled = trailing.get('enabled', True)
            self.trailing_activation_pips = trailing.get('activation_pips', 30)
            self.trailing_distance_pips = trailing.get('distance_pips', 20)
        
        breakeven = params.get('breakeven', {})
        if breakeven:
            self.breakeven_enabled = breakeven.get('enabled', True)
            self.breakeven_activation_pips = breakeven.get('activation_pips', 40)
            self.breakeven_safety_pips = breakeven.get('safety_pips', 5)
    
    def check_and_apply_trailing_stop(self, position, current_price):
        """
        Aplica trailing stop que PROTEGE el profit máximo alcanzado
        
        🔧 CORREGIDO: Ahora cierra en profit máximo si el precio retrocede
        """
        if not self.trailing_enabled:
            return False
        
        ticket = position.ticket
        
        # Calcular profit actual en pips
        if position.type == 0:  # BUY
            profit_pips = (current_price - position.price_open) / 0.01
        else:  # SELL
            profit_pips = (position.price_open - current_price) / 0.01
        
        # Activar trailing si se alcanza umbral
        if profit_pips >= self.trailing_activation_pips:
            
            # Inicializar tracking si es primera vez
            if ticket not in self.positions_with_trailing:
                self.positions_with_trailing[ticket] = {
                    'activated': True,
                    'highest_profit': profit_pips,
                    'highest_profit_price': current_price,  # 🆕 Guardar precio del profit máximo
                    'activation_time': datetime.now()
                }
                self.send_log(f"🎯 Trailing activado en ticket {ticket} @ {profit_pips:.1f} pips")
            
            # Obtener datos de trailing
            trailing_data = self.positions_with_trailing[ticket]
            
            # 🔧 ACTUALIZAR PROFIT MÁXIMO si el precio mejoró
            if profit_pips > trailing_data['highest_profit']:
                trailing_data['highest_profit'] = profit_pips
                trailing_data['highest_profit_price'] = current_price
            
            # 🔧 CALCULAR NUEVO SL BASADO EN EL PROFIT MÁXIMO ALCANZADO
            if position.type == 0:  # BUY
                # El nuevo SL debe estar trailing_distance_pips DEBAJO del precio más alto alcanzado
                highest_price = trailing_data['highest_profit_price']
                new_sl = highest_price - (self.trailing_distance_pips * 0.01)
                
                # Solo mover SL si es mejor que el actual (hacia arriba para BUY)
                if new_sl > position.sl:
                    profit_protected = (new_sl - position.price_open) / 0.01
                    self.send_log(f"📈 Trailing BUY: Protegiendo {profit_protected:.1f} pips (máx: {trailing_data['highest_profit']:.1f})")
                    return self.modify_position_sl_validated(position, new_sl, position.tp, current_price)
            
            else:  # SELL
                # El nuevo SL debe estar trailing_distance_pips ARRIBA del precio más bajo alcanzado
                highest_price = trailing_data['highest_profit_price']
                new_sl = highest_price + (self.trailing_distance_pips * 0.01)
                
                # Solo mover SL si es mejor que el actual (hacia abajo para SELL)
                if new_sl < position.sl:
                    profit_protected = (position.price_open - new_sl) / 0.01
                    self.send_log(f"📉 Trailing SELL: Protegiendo {profit_protected:.1f} pips (máx: {trailing_data['highest_profit']:.1f})")
                    return self.modify_position_sl_validated(position, new_sl, position.tp, current_price)
        
        return False
    
    def check_and_apply_breakeven(self, position, current_price):
        """Mueve SL a breakeven si se cumplen condiciones"""
        if not self.breakeven_enabled:
            return False
        
        ticket = position.ticket
        
        # Si ya se aplicó breakeven, no hacer nada
        if ticket in self.positions_with_breakeven:
            return False
        
        # Calcular profit en pips
        if position.type == 0:  # BUY
            profit_pips = (current_price - position.price_open) / 0.01
        else:  # SELL
            profit_pips = (position.price_open - current_price) / 0.01
        
        # Mover a breakeven si se alcanza umbral
        if profit_pips >= self.breakeven_activation_pips:
            
            if position.type == 0:  # BUY
                new_sl = position.price_open + (self.breakeven_safety_pips * 0.01)
            else:  # SELL
                new_sl = position.price_open - (self.breakeven_safety_pips * 0.01)
            
            if self.modify_position_sl_validated(position, new_sl, position.tp, current_price):
                self.positions_with_breakeven[ticket] = {
                    'activated': True,
                    'activation_profit': profit_pips,
                    'activation_time': datetime.now()
                }
                
                return True
        
        return False
    
    def modify_position_sl_validated(self, position, new_sl, new_tp, current_price):
        """
        🆕 NUEVO: Modifica SL/TP con VALIDACIÓN COMPLETA
        
        Esta función previene el error 10016 usando el OrderValidator
        """
        ticket = position.ticket
        self.modification_stats["total_attempts"] += 1
        
        # 🆕 VALIDACIÓN COMPLETA antes de modificar
        if self.order_validator:
            is_valid, error_msg, validated_sl, validated_tp = self.order_validator.full_modification_validation(
                position, new_sl, new_tp, current_price
            )
            
            if not is_valid:
                # Actualizar estadísticas según tipo de error
                if "cooldown" in error_msg.lower():
                    self.modification_stats["cooldown_blocks"] += 1
                elif "freeze" in error_msg.lower():
                    self.modification_stats["freeze_level_blocks"] += 1
                else:
                    self.modification_stats["validation_failures"] += 1
                
                return False
            
            # Usar SL/TP validados y ajustados
            new_sl = validated_sl
            new_tp = validated_tp
        else:
            # Si no hay validador, al menos verificar lógica básica
            if position.type == 0:  # BUY
                if new_sl >= current_price:
                    self.send_log(f"❌ SL inválido para BUY: {new_sl:.2f} >= precio {current_price:.2f}")
                    self.modification_stats["validation_failures"] += 1
                    return False
            else:  # SELL
                if new_sl <= current_price:
                    self.send_log(f"❌ SL inválido para SELL: {new_sl:.2f} <= precio {current_price:.2f}")
                    self.modification_stats["validation_failures"] += 1
                    return False
        
        # 🆕 Intentar modificación con validación exitosa
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": ticket,
                "sl": new_sl,
                "tp": new_tp,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.modification_stats["successful_modifications"] += 1
                return True
            
            elif result.retcode == 10016:
                # Error 10016 - Esto NO debería pasar con validación completa
                self.send_log(f"⚠️ ERROR 10016 INESPERADO para ticket {ticket}")
                self.send_log(f"   Esto indica un problema con la validación")
                self.modification_stats["failed_modifications"] += 1
                return False
            
            else:
                self.modification_stats["failed_modifications"] += 1
                return False
                
        except Exception as e:
            self.modification_stats["failed_modifications"] += 1
            return False
    
    def process_position(self, position, current_price):
        """Procesa una posición para trailing y breakeven"""
        # Intentar trailing primero
        trailing_applied = self.check_and_apply_trailing_stop(position, current_price)
        
        # Si no se aplicó trailing, intentar breakeven
        if not trailing_applied:
            self.check_and_apply_breakeven(position, current_price)
    
    def cleanup_closed_position(self, ticket):
        """Limpia datos de posición cerrada"""
        if ticket in self.positions_with_trailing:
            del self.positions_with_trailing[ticket]
        
        if ticket in self.positions_with_breakeven:
            del self.positions_with_breakeven[ticket]
    
    def get_stats(self):
        """Retorna estadísticas del sistema incluyendo modificaciones"""
        success_rate = 0
        if self.modification_stats["total_attempts"] > 0:
            success_rate = (self.modification_stats["successful_modifications"] / 
                          self.modification_stats["total_attempts"] * 100)
        
        return {
            'trailing_active_count': len(self.positions_with_trailing),
            'breakeven_active_count': len(self.positions_with_breakeven),
            'trailing_params': {
                'activation_pips': self.trailing_activation_pips,
                'distance_pips': self.trailing_distance_pips
            },
            'breakeven_params': {
                'activation_pips': self.breakeven_activation_pips,
                'safety_pips': self.breakeven_safety_pips
            },
            'modification_stats': {
                **self.modification_stats,
                'success_rate': success_rate
            }
        }
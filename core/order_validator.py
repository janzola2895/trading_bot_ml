"""
╔══════════════════════════════════════════════════════════════════════════╗
║             SISTEMA DE VALIDACIÓN DE ÓRDENES v5.2                        ║
║                                                                          ║
║  Sistema exhaustivo de validación para evitar errores 10027 y 10016     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5
from datetime import datetime
from config import (
    MAX_SPREAD_PIPS, MAX_RETRY_ATTEMPTS, RETRY_DELAY_SECONDS,
    MODIFICATION_COOLDOWN_SECONDS, MIN_DISTANCE_FROM_PRICE_PIPS,
    SYMBOL_CACHE_SECONDS
)


class OrderValidator:
    """
    Sistema exhaustivo de validación de órdenes para evitar errores 10027 y 10016
    
    🆕 CARACTERÍSTICAS v5.2 MEJORADO:
    - Validación de volumen según límites del símbolo
    - Validación de niveles SL/TP según STOP_LEVEL
    - Verificación de horario de trading
    - Validación de spread máximo
    - Verificación de conexión y estado del símbolo
    - 🆕 VALIDACIÓN DE MODIFICACIONES SL/TP (Fix error 10016)
    - 🆕 Verificación de FREEZE_LEVEL
    - 🆕 Sistema de cooldown entre modificaciones
    - Logs detallados de cada validación
    - Sistema de retry automático
    """
    
    def __init__(self, symbol="XAUUSD", logger=None):
        self.symbol = symbol
        self.logger = logger
        
        # Configuración de validación
        self.max_spread_pips = MAX_SPREAD_PIPS
        self.max_retry_attempts = MAX_RETRY_ATTEMPTS
        self.retry_delay_seconds = RETRY_DELAY_SECONDS
        
        # 🆕 Configuración para modificaciones
        self.modification_cooldown_seconds = MODIFICATION_COOLDOWN_SECONDS
        self.last_modification_time = {}  # ticket -> timestamp
        self.min_distance_from_price_pips = MIN_DISTANCE_FROM_PRICE_PIPS
        
        # Cache de información del símbolo
        self.symbol_info = None
        self.last_symbol_update = None
        self.symbol_cache_seconds = SYMBOL_CACHE_SECONDS
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)
    
    def update_symbol_info(self, force=False):
        """Actualiza información del símbolo"""
        now = datetime.now()
        
        if (force or 
            self.symbol_info is None or 
            self.last_symbol_update is None or
            (now - self.last_symbol_update).total_seconds() > self.symbol_cache_seconds):
            
            self.symbol_info = mt5.symbol_info(self.symbol)
            self.last_symbol_update = now
            
            if self.symbol_info is None:
                self.send_log(f"❌ No se pudo obtener información de {self.symbol}")
                return False
            
            return True
        
        return True
    
    def validate_connection(self):
        """Valida conexión con MT5"""
        if not mt5.terminal_info():
            self.send_log("❌ VALIDACIÓN: No hay conexión con MT5")
            return False, "No connection to MT5"
        
        return True, "Connection OK"
    
    def validate_symbol_availability(self):
        """Valida disponibilidad del símbolo"""
        if not self.update_symbol_info():
            return False, f"Symbol {self.symbol} not found"
        
        if not self.symbol_info.visible:
            self.send_log(f"⚠️ VALIDACIÓN: {self.symbol} no visible, intentando seleccionar...")
            if not mt5.symbol_select(self.symbol, True):
                return False, f"Cannot select symbol {self.symbol}"
            
            # Actualizar info después de seleccionar
            self.update_symbol_info(force=True)
        
        return True, "Symbol available"
    
    def validate_trading_allowed(self):
        """Valida si el trading está permitido"""
        if not self.symbol_info:
            return False, "Symbol info not available"
        
        # Verificar si el trading está permitido para el símbolo
        if self.symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            return False, "Trading disabled for symbol"
        
        if self.symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_CLOSEONLY:
            return False, "Only closing positions allowed"
        
        return True, "Trading allowed"
    
    def validate_market_open(self):
        """Valida si el mercado está abierto"""
        # Obtener tick reciente
        tick = mt5.symbol_info_tick(self.symbol)
        
        if tick is None:
            return False, "No market data available"
        
        # Verificar que el tick no sea muy antiguo (más de 5 minutos)
        tick_time = datetime.fromtimestamp(tick.time)
        now = datetime.now()
        
        if (now - tick_time).total_seconds() > 300:
            return False, f"Market data too old ({(now - tick_time).total_seconds():.0f}s)"
        
        # Verificar que haya bid y ask válidos
        if tick.bid == 0 or tick.ask == 0:
            return False, "Invalid bid/ask prices"
        
        return True, "Market open"
    
    def validate_spread(self):
        """Valida que el spread no sea excesivo"""
        tick = mt5.symbol_info_tick(self.symbol)
        
        if tick is None:
            return False, "No tick data", 0
        
        spread = tick.ask - tick.bid
        spread_pips = spread / (self.symbol_info.point * 10)
        
        if spread_pips > self.max_spread_pips:
            return False, f"Spread too high: {spread_pips:.1f} pips", spread_pips
        
        return True, f"Spread OK: {spread_pips:.1f} pips", spread_pips
    
    def validate_volume(self, volume):
        """Valida que el volumen esté dentro de los límites"""
        if not self.symbol_info:
            return False, "Symbol info not available", volume
        
        min_volume = self.symbol_info.volume_min
        max_volume = self.symbol_info.volume_max
        volume_step = self.symbol_info.volume_step
        
        # Verificar límites
        if volume < min_volume:
            self.send_log(f"⚠️ VALIDACIÓN: Volumen {volume} < mínimo {min_volume}")
            return False, f"Volume below minimum ({min_volume})", volume
        
        if volume > max_volume:
            self.send_log(f"⚠️ VALIDACIÓN: Volumen {volume} > máximo {max_volume}")
            return False, f"Volume above maximum ({max_volume})", volume
        
        # Normalizar volumen al step correcto
        normalized_volume = round(volume / volume_step) * volume_step
        normalized_volume = round(normalized_volume, 2)
        
        if abs(normalized_volume - volume) > 0.001:
            self.send_log(f"ℹ️ VALIDACIÓN: Volumen normalizado {volume} → {normalized_volume}")
        
        return True, f"Volume OK: {normalized_volume}", normalized_volume
    
    def validate_stop_levels(self, order_type, price, sl, tp):
        """Valida niveles de SL/TP según STOP_LEVEL del símbolo"""
        if not self.symbol_info:
            return False, "Symbol info not available", sl, tp
        
        stops_level = self.symbol_info.trade_stops_level
        point = self.symbol_info.point
        
        # Convertir stops_level a precio
        min_distance = stops_level * point
        
        # Si stops_level es 0, usar un mínimo razonable (10 pips para oro)
        if stops_level == 0:
            min_distance = 10 * point * 10  # 10 pips
        
        # 🆕 Agregar margen de seguridad adicional
        safety_margin = self.min_distance_from_price_pips * point * 10
        min_distance = max(min_distance, safety_margin)
        
        # Validar SL
        if sl > 0:
            if order_type == mt5.ORDER_TYPE_BUY:
                sl_distance = price - sl
                if sl_distance < min_distance:
                    self.send_log(f"⚠️ VALIDACIÓN: SL muy cerca del precio")
                    # Ajustar SL
                    sl = price - min_distance - (5 * point * 10)  # +5 pips de margen
                    self.send_log(f"   SL ajustado a: ${sl:.2f}")
            else:  # SELL
                sl_distance = sl - price
                if sl_distance < min_distance:
                    self.send_log(f"⚠️ VALIDACIÓN: SL muy cerca del precio")
                    sl = price + min_distance + (5 * point * 10)
                    self.send_log(f"   SL ajustado a: ${sl:.2f}")
        
        # Validar TP
        if tp > 0:
            if order_type == mt5.ORDER_TYPE_BUY:
                tp_distance = tp - price
                if tp_distance < min_distance:
                    self.send_log(f"⚠️ VALIDACIÓN: TP muy cerca del precio")
                    tp = price + min_distance + (5 * point * 10)
                    self.send_log(f"   TP ajustado a: ${tp:.2f}")
            else:  # SELL
                tp_distance = price - tp
                if tp_distance < min_distance:
                    self.send_log(f"⚠️ VALIDACIÓN: TP muy cerca del precio")
                    tp = price - min_distance - (5 * point * 10)
                    self.send_log(f"   TP ajustado a: ${tp:.2f}")
        
        return True, "Stop levels OK", sl, tp
    
    def validate_prices(self, order_type, price, sl, tp):
        """Valida que los precios sean lógicos"""
        # Validar que los precios no sean 0 o negativos
        if price <= 0:
            return False, "Invalid price"
        
        if order_type == mt5.ORDER_TYPE_BUY:
            if sl > 0 and sl >= price:
                return False, f"Invalid BUY: SL ({sl:.2f}) >= Price ({price:.2f})"
            if tp > 0 and tp <= price:
                return False, f"Invalid BUY: TP ({tp:.2f}) <= Price ({price:.2f})"
        else:  # SELL
            if sl > 0 and sl <= price:
                return False, f"Invalid SELL: SL ({sl:.2f}) <= Price ({price:.2f})"
            if tp > 0 and tp >= price:
                return False, f"Invalid SELL: TP ({tp:.2f}) >= Price ({price:.2f})"
        
        return True, "Prices valid"
    
    def full_validation(self, order_type, volume, price, sl, tp):
        """
        Validación completa antes de enviar orden
        
        Returns:
            tuple: (is_valid, error_message, validated_params)
        """
        self.send_log("🔍 Iniciando validación exhaustiva de orden...")
        
        # 1. Validar conexión
        valid, msg = self.validate_connection()
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 2. Validar símbolo
        valid, msg = self.validate_symbol_availability()
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 3. Validar trading permitido
        valid, msg = self.validate_trading_allowed()
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 4. Validar mercado abierto
        valid, msg = self.validate_market_open()
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 5. Validar spread
        valid, msg, spread = self.validate_spread()
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 6. Validar y normalizar volumen
        valid, msg, normalized_volume = self.validate_volume(volume)
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 7. Validar precios básicos
        valid, msg = self.validate_prices(order_type, price, sl, tp)
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # 8. Validar y ajustar niveles de stop
        valid, msg, adjusted_sl, adjusted_tp = self.validate_stop_levels(
            order_type, price, sl, tp
        )
        if not valid:
            return False, msg, None
        self.send_log(f"   ✅ {msg}")
        
        # Parámetros validados y ajustados
        validated_params = {
            'volume': normalized_volume,
            'sl': adjusted_sl,
            'tp': adjusted_tp,
            'spread_pips': spread
        }
        
        self.send_log("✅ Validación completa exitosa")
        return True, "All validations passed", validated_params
    
    # 🆕 NUEVOS MÉTODOS PARA VALIDAR MODIFICACIONES SL/TP
    
    def check_modification_cooldown(self, ticket):
        """
        🆕 Verifica si ha pasado suficiente tiempo desde la última modificación
        """
        if ticket not in self.last_modification_time:
            return True, "No previous modification"
        
        last_time = self.last_modification_time[ticket]
        elapsed = (datetime.now() - last_time).total_seconds()
        
        if elapsed < self.modification_cooldown_seconds:
            remaining = self.modification_cooldown_seconds - elapsed
            return False, f"Cooldown active: {remaining:.1f}s remaining"
        
        return True, "Cooldown passed"
    
    def validate_freeze_level(self, current_price, new_sl, new_tp, position_type):
        """
        🆕 Valida que SL/TP respeten el FREEZE_LEVEL
        El freeze level es la distancia mínima del precio actual donde no se pueden colocar órdenes
        """
        if not self.symbol_info:
            return False, "Symbol info not available"
        
        freeze_level = self.symbol_info.trade_freeze_level
        point = self.symbol_info.point
        
        # Si freeze_level es 0, no hay restricción
        if freeze_level == 0:
            return True, "No freeze level restriction"
        
        freeze_distance = freeze_level * point
        
        # Validar nuevo SL
        if new_sl > 0:
            sl_distance = abs(current_price - new_sl)
            if sl_distance < freeze_distance:
                return False, f"SL too close to price (freeze level: {freeze_level} points)"
        
        # Validar nuevo TP
        if new_tp > 0:
            tp_distance = abs(current_price - new_tp)
            if tp_distance < freeze_distance:
                return False, f"TP too close to price (freeze level: {freeze_level} points)"
        
        return True, "Freeze level OK"
    
    def validate_modification_stops(self, position, new_sl, new_tp, current_price):
        """
        🆕 Valida niveles de SL/TP para MODIFICACIÓN de posición existente
        
        Esta es la clave para evitar el error 10016
        """
        if not self.symbol_info:
            return False, "Symbol info not available", new_sl, new_tp
        
        stops_level = self.symbol_info.trade_stops_level
        point = self.symbol_info.point
        
        # Convertir stops_level a precio
        min_distance = stops_level * point
        
        # Si stops_level es 0, usar un mínimo razonable
        if stops_level == 0:
            min_distance = 10 * point * 10  # 10 pips
        
        # 🆕 Agregar margen de seguridad EXTRA para modificaciones
        safety_margin = self.min_distance_from_price_pips * point * 10
        min_distance = max(min_distance, safety_margin) + (5 * point * 10)  # +5 pips extra
        
        position_type = position.type
        
        # Validar nuevo SL
        if new_sl > 0:
            if position_type == 0:  # BUY
                # SL debe estar DEBAJO del precio actual
                if new_sl >= current_price:
                    self.send_log(f"❌ MODIFICACIÓN: SL BUY debe estar debajo del precio actual")
                    return False, "Invalid SL for BUY position", new_sl, new_tp
                
                sl_distance = current_price - new_sl
                
                if sl_distance < min_distance:
                    # Ajustar SL con más margen
                    new_sl = current_price - min_distance - (10 * point * 10)  # +10 pips extra
                
                # Verificar que el nuevo SL sea mejor o igual que el anterior
                if position.sl > 0 and new_sl < position.sl:
                    return False, "New SL worse than current", new_sl, new_tp
                    
            else:  # SELL
                # SL debe estar ARRIBA del precio actual
                if new_sl <= current_price:
                    self.send_log(f"❌ MODIFICACIÓN: SL SELL debe estar arriba del precio actual")
                    return False, "Invalid SL for SELL position", new_sl, new_tp
                
                sl_distance = new_sl - current_price
                
                if sl_distance < min_distance:
                    # Ajustar SL con más margen
                    new_sl = current_price + min_distance + (10 * point * 10)  # +10 pips extra
                
                # Verificar que el nuevo SL sea mejor o igual que el anterior
                if position.sl > 0 and new_sl > position.sl:
                    return False, "New SL worse than current", new_sl, new_tp
        
        # Validar nuevo TP (opcional, pero incluido por completitud)
        if new_tp > 0:
            if position_type == 0:  # BUY
                tp_distance = new_tp - current_price
                if tp_distance < min_distance:
                    new_tp = current_price + min_distance + (10 * point * 10)
                    self.send_log(f"⚠️ MODIFICACIÓN: TP ajustado a ${new_tp:.2f}")
            else:  # SELL
                tp_distance = current_price - new_tp
                if tp_distance < min_distance:
                    new_tp = current_price - min_distance - (10 * point * 10)
                    self.send_log(f"⚠️ MODIFICACIÓN: TP ajustado a ${new_tp:.2f}")
        
        return True, "Modification stops validated", new_sl, new_tp
    
    def full_modification_validation(self, position, new_sl, new_tp, current_price):
        """
        🆕 Validación COMPLETA antes de modificar SL/TP de una posición
        
        Esta función previene el error 10016
        
        Returns:
            tuple: (is_valid, error_message, validated_sl, validated_tp)
        """
        ticket = position.ticket
        
        # 1. Validar conexión
        valid, msg = self.validate_connection()
        if not valid:
            return False, msg, new_sl, new_tp
        
        # 2. Validar símbolo
        valid, msg = self.validate_symbol_availability()
        if not valid:
            return False, msg, new_sl, new_tp
        
        # 3. Validar mercado abierto
        valid, msg = self.validate_market_open()
        if not valid:
            return False, msg, new_sl, new_tp
        
        # 4. Verificar cooldown
        valid, msg = self.check_modification_cooldown(ticket)
        if not valid:
            return False, msg, new_sl, new_tp
        
        # 5. Validar freeze level
        valid, msg = self.validate_freeze_level(current_price, new_sl, new_tp, position.type)
        if not valid:
            return False, msg, new_sl, new_tp
        
        # 6. Validar y ajustar niveles de stop para modificación
        valid, msg, validated_sl, validated_tp = self.validate_modification_stops(
            position, new_sl, new_tp, current_price
        )
        if not valid:
            return False, msg, new_sl, new_tp
        
        # Registrar timestamp de modificación
        self.last_modification_time[ticket] = datetime.now()
        
        return True, "Modification validated", validated_sl, validated_tp
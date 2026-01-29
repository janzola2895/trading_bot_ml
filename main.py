import MetaTrader5 as mt5
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
import tkinter as tk

# Imports propios
from config import *
from utils.logger import BotLogger
from utils.helpers import *
from strategy_stats_manager import StrategyStatsManager

from core.order_validator import OrderValidator
from core.trailing_breakeven import TrailingStopBreakevenSystem
from core.memory import TradingMemory, ProfitTracker
from core.ml_optimizer import MLParameterOptimizer
from core.global_strategy_cooldown import GlobalStrategyCooldown

# v6.0: NUEVOS SISTEMAS
from core.sltp_calculator import SLTPCalculator
from core.ml_validator import MLSignalValidator
from core.correlation_manager import CorrelationManager
from core.equity_monitor import EquityMonitor
from core.news_filter import EconomicNewsFilter

from strategies.ml_strategy import MLEnsemble, IncrementalLearningSystem
from strategies.support_resistance import SupportResistanceSystem
from strategies.fibonacci import FibonacciRetracementSystem
from strategies.price_action import PriceActionSystem
from strategies.candlestick import CandlestickPatternSystem
from strategies.liquidity import LiquiditySystem

from analysis.mtf_analyzer import MultiTimeframeAnalyzer
from analysis.signal_aggregator import SignalAggregator

from gui.main_window import EnhancedTradingBotGUI


class MLTradingBot:
    """
    Bot de Trading ML v6.0.1 - COMPLETO CON MEJORAS AVANZADAS
    
    🆕 v6.0.1: COOLDOWN GLOBAL CORREGIDO
    - Registro correcto de operaciones ejecutadas
    - Cooldown independiente por estrategia (15-60 min)
    - Visualización de tiempo restante en GUI
    - SL/TP dinámico por estrategia y ATR
    - Validación ML de todas las señales
    - Gestión de correlación y riesgo
    - Monitoreo de equity en tiempo real
    - Filtro de noticias económicas
    - Trailing stop dinámico con ATR
    """
    
    def __init__(self, gui_queue=None):
        self.gui_queue = gui_queue
        
        # Logger
        self.logger = BotLogger(gui_queue=gui_queue)
        
        # Configuración básica
        self.account = MT5_ACCOUNT
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self.symbol = SYMBOL
        self.timeframe = TIMEFRAME
        self.lot_size = DEFAULT_LOT_SIZE
        self.max_daily_profit = DEFAULT_MAX_DAILY_PROFIT
        self.max_daily_loss = DEFAULT_MAX_DAILY_LOSS
        self.daily_profit = 0.0
        self.trading_enabled = True
        self.magic_number = MAGIC_NUMBER
        
        # Sistema de validación de órdenes
        self.order_validator = OrderValidator(symbol=self.symbol, logger=self.logger)

        # 🆕 v6.0.1: Sistema de cooldown global
        self.global_cooldown = GlobalStrategyCooldown(logger=self.logger)
        
        # Sistemas principales
        self.memory = TradingMemory(DATA_DIR)
        self.ensemble = MLEnsemble(DATA_DIR, logger=self.logger)
        
        # Sistema de aprendizaje INCREMENTAL
        self.incremental_learning = IncrementalLearningSystem(
            self.memory,
            self.ensemble,
            retrain_every=RETRAIN_EVERY_N_OPS,
            logger=self.logger
        )
        
        self.profit_tracker = ProfitTracker(DATA_DIR)
        self.ml_optimizer = MLParameterOptimizer(DATA_DIR)
        
        # Sistema Multi-Timeframe
        self.mtf_analyzer = MultiTimeframeAnalyzer(
            symbol=self.symbol,
            logger=self.logger
        )
        
        # 6 Estrategias
        self.sr_system = SupportResistanceSystem()
        self.fib_system = FibonacciRetracementSystem()
        self.pa_system = PriceActionSystem()
        self.candlestick_system = CandlestickPatternSystem()
        self.liquidity_system = LiquiditySystem()
        
        # Sistema de Trailing Stop y Breakeven CON VALIDACIÓN
        self.trailing_breakeven = TrailingStopBreakevenSystem(
            order_validator=self.order_validator,
            logger=self.logger
        )
        
        # v6.0: NUEVOS SISTEMAS AVANZADOS
        self.sltp_calculator = SLTPCalculator(
            symbol=self.symbol,
            logger=self.logger
        )
        
        self.ml_validator = MLSignalValidator(
            ml_ensemble=self.ensemble,
            logger=self.logger,
            enabled=True
        )
        
        self.correlation_manager = CorrelationManager(
            logger=self.logger
        )
        
        self.equity_monitor = EquityMonitor(
            memory=self.memory,
            logger=self.logger
        )
        
        self.news_filter = EconomicNewsFilter(
            data_dir=DATA_DIR,
            logger=self.logger
        )
        
        # Control de estrategias
        self.strategies_enabled = {
            'ml': True,
            'sr': True,
            'fibo': True,
            'price_action': True,
            'candlestick': True,
            'liquidity': True
        }
        
        self.mtf_enabled = True
        self.max_total_positions = DEFAULT_MAX_POSITIONS
        
        # Signal Aggregator con MTF, TIMEOUT y COOLDOWN
        self.signal_aggregator = SignalAggregator(
            self.ensemble,
            self.sr_system,
            self.fib_system,
            self.pa_system,
            self.candlestick_system,
            self.liquidity_system,
            self.mtf_analyzer,
            global_cooldown=self.global_cooldown,  # 🆕 v6.0.1
            logger=self.logger
        )
        self.signal_aggregator.set_mtf_enabled(self.mtf_enabled)
        
        # Tracking de operaciones
        self.active_trades = {}
        self.closed_trades_history = {}

        # 🆕 NUEVO: Gestor persistente de estadísticas por estrategia
        self.stats_manager = StrategyStatsManager(DATA_DIR)
        self.strategy_stats_tracker = self.stats_manager.get_stats()
    
        self.is_connected = False
        
        # Variable para almacenar market_state actual
        self.market_state = {}

    def send_strategy_stats(self):
        """
        🔧 v6.0.1: Envía estadísticas CON COOLDOWN REMAINING
        """
        # Obtener estadísticas base
        stats = self.strategy_stats_tracker.copy()
        
        # 🆕 AGREGAR COOLDOWN REMAINING A CADA ESTRATEGIA
        strategy_mapping = {
            'ml': 'ml',
            'price_action': 'price_action',
            'sr': 'sr',
            'candlestick': 'candlestick',
            'fibo': 'fibo',
            'liquidity': 'liquidity'
        }
        
        for internal_name, strategy_key in strategy_mapping.items():
            if strategy_key in stats:
                # Obtener estado de cooldown
                status = self.global_cooldown.get_strategy_status(internal_name)
                
                # Agregar tiempo restante en minutos
                time_remaining = status.get('time_remaining', 0)
                stats[strategy_key]['cooldown_remaining'] = time_remaining
        
        # Enviar a GUI
        self.send_to_gui('strategy_stats', stats=stats)
    
    def update_strategy_stat(self, strategy, profit, result):
        """
        Actualiza estadísticas de una estrategia cuando se cierra una operación
        
        Args:
            strategy: Nombre de la estrategia ('ml', 'sr', 'fibo', etc.)
            profit: Profit de la operación
            result: 'win' o 'loss' o 'breakeven'
        """
        if strategy not in self.strategy_stats_tracker:
            self.logger.warning(f"⚠️ Estrategia desconocida: {strategy}")
            return
        
        # 🆕 Actualizar usando gestor persistente
        self.stats_manager.update_result(strategy, profit, result)
        self.strategy_stats_tracker = self.stats_manager.get_stats()

        self.send_strategy_stats()
        
        self.logger.info(f"📊 Stats {strategy.upper()}: {self.strategy_stats_tracker[strategy]['operations']} ops | {self.strategy_stats_tracker[strategy]['wins']}W/{self.strategy_stats_tracker[strategy]['losses']}L | ${self.strategy_stats_tracker[strategy]['profit']:.2f}")

    def connect(self):
        """Conecta a MT5"""
        if not mt5.initialize():
            self.logger.error("Error inicializando MT5")
            return False
        
        authorized = mt5.login(self.account, password=self.password, server=self.server)
        
        if authorized:
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                self.logger.error(f"Símbolo {self.symbol} no encontrado")
                return False
            
            if not symbol_info.visible:
                if not mt5.symbol_select(self.symbol, True):
                    self.logger.error(f"No se pudo seleccionar {self.symbol}")
                    return False
            
            test_data = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 10)
            if test_data is None:
                self.logger.error(f"No se pueden obtener datos de {self.symbol}")
                return False
            
            self.logger.success(f"✅ Conectado - Cuenta: {self.account}")
            self.send_to_gui('status', connected=True)
            self.is_connected = True
            self.logger.info("🎖️ SISTEMA v6.0.1: COOLDOWN GLOBAL CORREGIDO")
            self.logger.info(f"   ✅ Registro correcto de operaciones ejecutadas")
            self.logger.info(f"   ✅ Cooldown independiente por estrategia (15-60 min)")
            self.logger.info(f"   ✅ Visualización de tiempo restante en GUI")
            self.logger.info(f"   ✅ SL/TP Dinámico por estrategia")
            self.logger.info(f"   ✅ Validación ML de señales")
            self.logger.info(f"   ✅ Gestión de correlación")
            self.logger.info(f"   ✅ Monitoreo de equity")
            self.logger.info(f"   ✅ Filtro de noticias")
            self.logger.info(f"   ✅ Trailing stop dinámico ATR")
            self.logger.info(f"📊 Multi-Timeframe: Prioritario | Req: {MTF_REQUIRED_HIGHER_TF}/{3} superiores + {MTF_REQUIRED_LOWER_TF}/{2} inferiores")
            self.logger.info(f"💰 Símbolo: {self.symbol} - Spread: {symbol_info.spread} pips")
            
            self.send_ml_status()
            return True
        else:
            error = mt5.last_error()
            self.logger.error(f"❌ Error login: {error}")
            return False
    
    def disconnect(self):
        """Desconecta de MT5"""
        mt5.shutdown()
        self.logger.info("🔌 Desconectado de MT5")
        self.send_to_gui('status', connected=False)
        self.is_connected = False
    
    def send_to_gui(self, msg_type, **kwargs):
        """Envía mensaje a la GUI"""
        if self.gui_queue:
            self.gui_queue.put({'type': msg_type, **kwargs})
    
    def send_ml_status(self):
        """Envía estado ML a GUI"""
        perf = self.memory.get_performance_metrics()
        models_comp = self.ensemble.get_models_comparison()
        rotation_status = self.ensemble.get_rotation_status()
        
        ml_status = {
            "performance": perf,
            "models": models_comp,
            "active_model": self.ensemble.active_model,
            "rotation_status": rotation_status
        }
        
        self.send_to_gui('ml_status', data=ml_status)
    
    def send_profit_charts_data(self):
        """Envía datos de gráficas"""
        hours, hourly_profits = self.profit_tracker.get_hourly_data()
        days, daily_profits = self.profit_tracker.get_daily_data()
        
        self.send_to_gui('profit_charts', hourly=hourly_profits, daily=daily_profits)
    
    def send_signal_stats(self):
        """Envía estadísticas de señales"""
        stats = self.signal_aggregator.get_stats()
        self.send_to_gui('signal_stats',
                        total=stats['total_signals_detected'],
                        executed=stats['total_signals_executed'])
    
    def send_autonomy_data(self):
        """Envía datos de autonomía"""
        autonomy_status = self.ml_optimizer.get_autonomy_status()
        learned_params = self.ml_optimizer.get_current_params()
        initial_params = self.ml_optimizer.initial_params
        recent_decisions = self.ml_optimizer.get_recent_decisions()
        
        data = {
            "autonomy_status": autonomy_status,
            "learned_params": learned_params,
            "initial_params": initial_params,
            "recent_decisions": recent_decisions
        }
        
        self.send_to_gui('autonomy_data', data=data)
    
    def update_config(self, max_profit, max_loss, lot_size, max_positions):
        """Actualiza configuración"""
        self.max_daily_profit = max_profit
        self.max_daily_loss = max_loss
        self.lot_size = lot_size
        self.max_total_positions = max_positions
        
        if not self.trading_enabled:
            within_profit = self.daily_profit < max_profit
            within_loss = self.daily_profit > -max_loss
            
            if within_profit and within_loss:
                self.trading_enabled = True
                self.logger.success("✔️✔️✔️ Trading RE-HABILITADO ✔️✔️✔️")
        
        self.logger.info(f"⚙️ Config: Lote={lot_size:.2f}, Max +${max_profit:.0f}, -${max_loss:.0f}, Ops:{max_positions}")
    
    def update_strategy_config(self, config):
        """Actualiza configuración de estrategias"""
        self.strategies_enabled['ml'] = config.get('ml_enabled', True)
        self.strategies_enabled['sr'] = config.get('sr_enabled', True)
        self.strategies_enabled['fibo'] = config.get('fibo_enabled', True)
        self.strategies_enabled['price_action'] = config.get('pa_enabled', True)
        self.strategies_enabled['candlestick'] = config.get('candlestick_enabled', True)
        self.strategies_enabled['liquidity'] = config.get('liquidity_enabled', True)
        
        self.sr_system.enabled = self.strategies_enabled['sr']
        self.fib_system.enabled = self.strategies_enabled['fibo']
        self.pa_system.enabled = self.strategies_enabled['price_action']
        self.candlestick_system.enabled = self.strategies_enabled['candlestick']
        self.liquidity_system.enabled = self.strategies_enabled['liquidity']
        
        self.mtf_enabled = config.get('mtf_enabled', True)
        
        active_count = sum(self.strategies_enabled.values())
        mtf_status = "MTF ON" if self.mtf_enabled else "MTF OFF"
        self.logger.info(f"🎯 Estrategias: {active_count}/6 | Max: {self.max_total_positions} | {mtf_status}")
        self.signal_aggregator.set_mtf_enabled(self.mtf_enabled)
    
    def reset_trading_manual(self):
        """Resetea trading manualmente"""
        self.trading_enabled = True
        self.logger.info("🔄 Trading RESETEADO manualmente")
    
    def reset_autonomy(self):
        """Resetea autonomía ML"""
        self.ml_optimizer = MLParameterOptimizer(DATA_DIR)
        self.trailing_breakeven.update_params(self.ml_optimizer.initial_params)
        
        self.logger.info("🔧 Sistema de autonomía ML reseteado a modo MANUAL")
        self.send_autonomy_data()
    
    def check_daily_limits(self):
        """Verifica límites diarios"""
        if self.daily_profit >= self.max_daily_profit:
            if self.trading_enabled:
                self.trading_enabled = False
                self.logger.success(f"🎯 OBJETIVO ALCANZADO! ${self.daily_profit:.2f}")
                self.logger.warning("⚠️ Trading deshabilitado")
            return True
        
        if self.daily_profit <= -self.max_daily_loss:
            if self.trading_enabled:
                self.trading_enabled = False
                self.logger.error(f"🛑 LÍMITE DE PÉRDIDA! ${self.daily_profit:.2f}")
                self.logger.warning("⚠️ Trading deshabilitado")
            return True
        
        return False
    
    def calculate_daily_profit(self):
        """Calcula profit diario"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            history = mt5.history_deals_get(today_start, datetime.now())
            
            if history:
                bot_deals = [deal for deal in history
                           if deal.magic == self.magic_number
                           and deal.entry == 1]
                total = sum(deal.profit for deal in bot_deals)
                self.daily_profit = total
                
                self.profit_tracker.reset_if_new_day()
                self.profit_tracker.update_hourly_profit(total)
                self.profit_tracker.update_daily_profit(total)
                
                return total
            
            return 0.0
        except Exception as e:
            self.logger.error(f"❌ Error calculando ganancia: {e}")
            return 0.0
    
    def get_historical_data(self, bars=1000):
        """Obtiene datos históricos"""
        if not self.is_connected:
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos"""
        import ta
        
        df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_high'] = bollinger.bollinger_hband()
        df['bb_low'] = bollinger.bollinger_lband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['momentum'] = df['close'].pct_change(periods=10)
        
        return df
    
    def create_features(self, df):
        """Crea features para ML"""
        df = self.calculate_indicators(df)
        df['price_to_ema21'] = (df['close'] - df['ema_21']) / df['ema_21']
        df['price_to_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
        df['ema_diff'] = (df['ema_21'] - df['ema_50']) / df['ema_50']
        df['bb_position'] = (df['close'] - df['bb_low']) / (df['bb_high'] - df['bb_low'])
        df['volume_change'] = df['tick_volume'].pct_change()
        df.dropna(inplace=True)
        return df
    
    def create_target(self, df, forward_bars=5, threshold=0.002):
        """Crea target para entrenamiento"""
        df['future_return'] = df['close'].shift(-forward_bars) / df['close'] - 1
        df['target'] = 0
        df.loc[df['future_return'] > threshold, 'target'] = 1
        df.loc[df['future_return'] < -threshold, 'target'] = -1
        return df
    
    def prepare_features_for_prediction(self, df):
        """Prepara features para predicción"""
        last_row = df.iloc[-1]
        
        features = {
            'ema_21': float(last_row['ema_21']),
            'ema_50': float(last_row['ema_50']),
            'atr': float(last_row['atr']),
            'adx': float(last_row['adx']),
            'rsi': float(last_row['rsi']),
            'macd': float(last_row['macd']),
            'macd_signal': float(last_row['macd_signal']),
            'momentum': float(last_row['momentum']),
            'price_to_ema21': float(last_row['price_to_ema21']),
            'price_to_ema50': float(last_row['price_to_ema50']),
            'ema_diff': float(last_row['ema_diff']),
            'bb_position': float(last_row['bb_position']),
            'volume_change': float(last_row['volume_change'])
        }
        
        return features
    
    def get_market_state(self, df):
        """Obtiene estado del mercado"""
        last_row = df.iloc[-1]
        
        if last_row['ema_21'] > last_row['ema_50']:
            trend = "uptrend"
        elif last_row['ema_21'] < last_row['ema_50']:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        atr_avg = df['atr'].tail(20).mean()
        if last_row['atr'] > atr_avg * 1.5:
            volatility = "high"
        elif last_row['atr'] < atr_avg * 0.5:
            volatility = "low"
        else:
            volatility = "normal"
        
        if last_row['adx'] > 25:
            strength = "strong"
        elif last_row['adx'] > 15:
            strength = "moderate"
        else:
            strength = "weak"
        
        return {
            "trend": trend,
            "volatility": volatility,
            "strength": strength,
            "rsi": float(last_row['rsi']),
            "adx": float(last_row['adx']),
            "atr": float(last_row['atr'])
        }
    
    def send_order(self, order_type, volume, sl_pips=70, tp_pips=140, strategy="unknown", 
                   signal_data=None, market_state=None, df=None):
        """
        🎖️ v6.0: Envía orden con SL/TP DINÁMICO y AJUSTE DE EQUITY
        
        MEJORAS:
        - Usa sltp_calculator para SL/TP dinámico por estrategia
        - Ajusta tamaño de lote según equity_monitor
        - Mantiene validación completa y retry automático
        """
        
        # 🎯 PASO 1: CALCULAR SL/TP DINÁMICO si está habilitado
        if signal_data and market_state and df is not None and USE_DYNAMIC_SLTP:
            try:
                sltp_result = self.sltp_calculator.calculate_sltp(
                    strategy=strategy,
                    signal_data=signal_data,
                    market_state=market_state,
                    df=df
                )
                
                sl_pips = sltp_result['sl_pips']
                tp_pips = sltp_result['tp_pips']
                
                self.logger.info(f"🎯 SL/TP Dinámico [{strategy.upper()}]: SL={sl_pips}p | TP={tp_pips}p | R:R={sltp_result['risk_reward']:.2f}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Error calculando SL/TP dinámico: {e}")
                # Continuar con valores por defecto
        
        # 🎯 PASO 2: AJUSTAR TAMAÑO DE LOTE según equity
        lot_multiplier = self.equity_monitor.get_lot_multiplier()
        adjusted_volume = volume * lot_multiplier
        
        if lot_multiplier != 1.0:
            mode = self.equity_monitor.determine_trading_mode()
            self.logger.info(f"📰 Lote ajustado por equity ({mode}): {volume:.2f} → {adjusted_volume:.2f}")
        
        # Obtener tick actual
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            self.logger.error("❌ No se pudo obtener tick del mercado")
            return None
        
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        point = self.order_validator.symbol_info.point if self.order_validator.symbol_info else 0.01
        
        # Calcular SL y TP
        if order_type == mt5.ORDER_TYPE_BUY:
            sl = price - sl_pips * point * 10
            tp = price + tp_pips * point * 10
        else:
            sl = price + sl_pips * point * 10
            tp = price - tp_pips * point * 10
        
        # PASO 3: VALIDACIÓN COMPLETA
        is_valid, error_msg, validated_params = self.order_validator.full_validation(
            order_type, adjusted_volume, price, sl, tp
        )
        
        if not is_valid:
            self.logger.error(f"❌ VALIDACIÓN FALLIDA: {error_msg}")
            return None
        
        normalized_volume = validated_params['volume']
        adjusted_sl = validated_params['sl']
        adjusted_tp = validated_params['tp']
        
        self.logger.success("✅ Validación completa exitosa - Iniciando envío de orden...")
        
        # Determinar filling types
        symbol_info = self.order_validator.symbol_info
        filling_type = symbol_info.filling_mode
        filling_modes = []
        
        if filling_type & 1:
            filling_modes.append(mt5.ORDER_FILLING_FOK)
        if filling_type & 2:
            filling_modes.append(mt5.ORDER_FILLING_IOC)
        if filling_type & 4:
            filling_modes.append(mt5.ORDER_FILLING_RETURN)
        
        if not filling_modes:
            filling_modes = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC]
        
        max_attempts = self.order_validator.max_retry_attempts
        
        # PASO 4: INTENTAR ENVIAR ORDEN CON RETRY
        for attempt in range(1, max_attempts + 1):
            self.logger.info(f"🎤 Intento {attempt}/{max_attempts} de envío de orden...")
            
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                self.logger.warning(f"⚠️ No se pudo actualizar precio en intento {attempt}")
                if attempt < max_attempts:
                    time.sleep(self.order_validator.retry_delay_seconds)
                    continue
                else:
                    return None
            
            current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
            
            for fill_mode in filling_modes:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": normalized_volume,
                    "type": order_type,
                    "price": current_price,
                    "sl": adjusted_sl,
                    "tp": adjusted_tp,
                    "deviation": 20,
                    "magic": self.magic_number,
                    "comment": f"{strategy.upper()}-v6.0.1-{attempt}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": fill_mode,
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    order_name = "🎉 COMPRA" if order_type == mt5.ORDER_TYPE_BUY else "🔥 VENTA"
                    self.logger.success(f"{order_name} EXITOSA!")
                    self.logger.info(f"   Ticket: {result.order} | Vol: {normalized_volume} @ ${current_price:.2f}")
                    self.logger.info(f"   SL: ${adjusted_sl:.2f} ({sl_pips}p) | TP: ${adjusted_tp:.2f} ({tp_pips}p)")
                    
                    return {
                        "result": result,
                        "sl": adjusted_sl,
                        "tp": adjusted_tp,
                        "price": current_price,
                        "sl_pips": sl_pips,
                        "tp_pips": tp_pips
                    }
                
                elif result.retcode == 10027:
                    self.logger.warning(f"⚠️ Error 10027 con modo {fill_mode}")
                    continue
                
                elif result.retcode == 10030:
                    continue
                
                else:
                    self.logger.warning(f"⚠️ Error {result.retcode}: {result.comment}")
                    break
            
            if attempt < max_attempts:
                self.logger.info(f"⏳ Reintentando en {self.order_validator.retry_delay_seconds}s...")
                time.sleep(self.order_validator.retry_delay_seconds)
            else:
                self.logger.error(f"❌ ORDEN RECHAZADA después de {max_attempts} intentos")
        
        return None
    
    def open_trade_from_signal(self, signal_data, features, market_state, df):
        """
        🎯 v6.0.1: Abre operación basada en señal CON RE-VALIDACIÓN
        
        PROCESO:
        1. Verificar antigüedad de señal
        2. RE-VALIDAR condiciones actuales
        3. Si pasa re-validación → ejecutar
        4. 🔧 CRÍTICO: REGISTRAR EN COOLDOWN después de ejecutar
        5. Si falla re-validación → descartar con log claro
        """
        signal = signal_data['signal']
        confidence = signal_data['confidence']
        strategy = signal_data['strategy']
        sl_pips = signal_data.get('sl_pips', 70)
        tp_pips = signal_data.get('tp_pips', 140)
        reason = signal_data.get('reason', '')
        
        mtf_status = signal_data.get('mtf_status', 'unknown')
        mtf_analysis = signal_data.get('mtf_analysis', {})
        
        # PASO 1: Verificar antigüedad de señal
        if 'timestamp' in signal_data:
            signal_age_seconds = self.signal_aggregator.get_signal_age_seconds(signal_data)
            signal_age_minutes = signal_age_seconds / 60
            
            if signal_age_seconds > 0:
                self.logger.info(f"⏰ Señal generada hace {signal_age_minutes:.1f} min")
        
        # PASO 2: RE-VALIDAR SEÑAL ANTES DE EJECUTAR
        self.logger.info(f"🔍 RE-VALIDANDO señal {strategy.upper()} antes de ejecutar...")
        
        tick = mt5.symbol_info_tick(self.symbol)
        current_price = tick.bid if tick else 0
        
        is_valid, revalidation_reason = self.signal_aggregator.revalidate_signal(
            signal_data, df, current_price, market_state, features
        )
        
        if not is_valid:
            # SEÑAL NO PASÓ RE-VALIDACIÓN
            signal_dir = "BUY" if signal == 1 else "SELL"
            self.logger.warning("")
            self.logger.warning(f"❌ SEÑAL DESCARTADA POR RE-VALIDACIÓN ❌")
            self.logger.warning(f"   Estrategia: {strategy.upper()} {signal_dir}")
            self.logger.warning(f"   Razón original: {reason}")
            self.logger.warning(f"   Razón rechazo: {revalidation_reason}")
            if 'timestamp' in signal_data:
                self.logger.warning(f"   Antigüedad: {signal_age_minutes:.1f} min")
            self.logger.warning("")
            
            return False
        
        # SEÑAL PASÓ RE-VALIDACIÓN - PROCEDER A EJECUTAR
        self.logger.success(f"✅ RE-VALIDACIÓN EXITOSA: {revalidation_reason}")
        
        order_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
        
        self.logger.info(f"📤 Intentando abrir: {reason}")
        
        # 🔧 Enviar orden con SL/TP dinámico y ajuste de equity
        order_result = self.send_order(
            order_type,
            self.lot_size,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            strategy=strategy,
            signal_data=signal_data,
            market_state=market_state,
            df=df
        )
        
        if order_result and order_result["result"].retcode == mt5.TRADE_RETCODE_DONE:
            result = order_result["result"]
            
            # 🔧 CRÍTICO v6.0.1: REGISTRAR EN COOLDOWN INMEDIATAMENTE
            self.signal_aggregator.mark_signal_as_executed(signal_data)
            
            current_params = self.ml_optimizer.get_current_params()
            
            trade_id = self.memory.add_trade_entry(
                features=features,
                signal=signal,
                confidence=confidence,
                market_state=market_state,
                strategy=strategy,
                trailing_params=current_params.get('trailing_stop', {}),
                breakeven_params=current_params.get('breakeven', {}),
                lot_params={
                    'lot_size': self.lot_size,
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips
                },
                htf_bias={
                    'status': mtf_status,
                    'analysis': mtf_analysis,
                    'enabled': self.mtf_enabled
                }
            )
            
            self.active_trades[result.order] = {
                "trade_id": trade_id,
                "open_time": datetime.now(),
                "features": features,
                "strategy": strategy,
                "signal": signal,
                "sl_pips": sl_pips,
                "tp_pips": tp_pips,
                "sl": order_result["sl"],
                "tp": order_result["tp"],
                "price_open": order_result["price"],
                "confidence": confidence,
                "mtf_status": mtf_status,
                "mtf_analysis": mtf_analysis,
                "signal_age_at_execution": signal_age_seconds if 'timestamp' in signal_data else 0
            }

            # 🆕 v6.0 FIX: Incrementar operations al ABRIR (no al cerrar)
            if strategy in self.strategy_stats_tracker:
                self.strategy_stats_tracker[strategy]['operations'] += 1
                self.send_strategy_stats()
            
            self.signal_aggregator.total_signals_executed += 1
            
            mtf_text = signal_data.get('mtf_reason', '')
            self.logger.success(f"✅ OPERACIÓN ABIERTA! {mtf_text} | {reason}")
            
            if 'timestamp' in signal_data:
                self.logger.info(f"   ✔️ Re-validada después de {signal_age_minutes:.1f} min")
            
            return True
        
        else:
            self.logger.error(f"❌ FALLO al abrir: {reason}")
            return False
    
    def check_positions(self):
        """
        🎖️ v6.0: Verifica y actualiza posiciones abiertas
        - Actualiza ATR para trailing dinámico
        - Procesa trailing stop y breakeven
        """
        positions = mt5.positions_get(symbol=self.symbol)
        
        tick = mt5.symbol_info_tick(self.symbol)
        current_price = tick.bid if tick else 0
        
        # 🎖️ Actualizar ATR para trailing dinámico
        if self.market_state and 'atr' in self.market_state:
            self.trailing_breakeven.update_atr(self.market_state['atr'])
        
        all_operations = []
        
        if positions:
            for pos in positions:
                self.trailing_breakeven.process_position(pos, current_price)
                
                if pos.type == 0:
                    pips = (current_price - pos.price_open) / 0.01
                else:
                    pips = (pos.price_open - current_price) / 0.01
                
                trade_info = self.active_trades.get(pos.ticket, {})
                strategy = extract_strategy_from_comment(pos.comment)
                if strategy == 'unknown':
                    strategy = trade_info.get('strategy', 'unknown')
                
                trailing_active = pos.ticket in self.trailing_breakeven.positions_with_trailing
                breakeven_active = pos.ticket in self.trailing_breakeven.positions_with_breakeven
                
                mtf_status = trade_info.get('mtf_status', 'unknown')
                
                all_operations.append({
                    'estado': '🟢 ABIERTA',
                    'estrategia': strategy.upper(),
                    'tipo': "🟢 BUY" if pos.type == 0 else "🔴 SELL",
                    'precio_entrada': pos.price_open,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'precio_actual': current_price,
                    'volumen': pos.volume,
                    'ganancia': pos.profit,
                    'trailing_active': trailing_active,
                    'breakeven_active': breakeven_active,
                    'mtf_status': mtf_status,
                    'pips': pips,
                    'hora': datetime.fromtimestamp(pos.time).strftime("%H:%M:%S")
                })
        
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            history = mt5.history_deals_get(today_start, datetime.now())
            
            if history:
                bot_deals = [deal for deal in history
                           if deal.magic == self.magic_number
                           and deal.entry == 1]
                
                bot_deals = sorted(bot_deals, key=lambda x: x.time, reverse=True)[:20]
                
                for deal in bot_deals:
                    if deal.position_id in self.closed_trades_history:
                        trade_info = self.closed_trades_history[deal.position_id]
                    else:
                        trade_info = self.active_trades.get(deal.position_id, {})
                    
                    strategy = extract_strategy_from_comment(deal.comment)
                    if strategy == 'unknown':
                        strategy = trade_info.get('strategy', 'unknown')
                    
                    mtf_status = trade_info.get('mtf_status', 'unknown')
                    
                    precio_entrada = trade_info.get('price_open', 0)
                    sl = trade_info.get('sl', 0)
                    tp = trade_info.get('tp', 0)
                    
                    all_operations.append({
                        'estado': '✅ CERRADA',
                        'estrategia': strategy.upper(),
                        'tipo': "🟢 BUY" if deal.type == 1 else "🔴 SELL",
                        'precio_entrada': precio_entrada,
                        'sl': sl,
                        'tp': tp,
                        'precio_actual': deal.price,
                        'volumen': deal.volume,
                        'ganancia': deal.profit,
                        'trailing_active': False,
                        'breakeven_active': False,
                        'mtf_status': mtf_status,
                        'pips': 0,
                        'hora': datetime.fromtimestamp(deal.time).strftime("%H:%M:%S")
                    })
        except:
            pass
        
        self.send_to_gui('positions', positions=all_operations)
        
        return positions if positions else []
    
    def check_and_close_trades(self):
        """Verifica operaciones cerradas y actualiza memoria"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        history = mt5.history_deals_get(today_start, datetime.now())
        
        if not history:
            return
        
        closed_deals = [deal for deal in history
                    if deal.magic == self.magic_number
                    and deal.entry == 1]
        
        for deal in closed_deals:
            if deal.position_id in self.active_trades:
                trade_info = self.active_trades[deal.position_id]
                
                profit = deal.profit
                result = "win" if profit > 0 else ("loss" if profit < 0 else "breakeven")
                duration = (datetime.now() - trade_info["open_time"]).total_seconds() / 60
                
                strategy = extract_strategy_from_comment(deal.comment)
                if strategy == 'unknown' and deal.position_id in self.active_trades:
                    strategy = self.active_trades[deal.position_id].get("strategy", "unknown")
                
                trailing_triggered = deal.position_id in self.trailing_breakeven.positions_with_trailing
                breakeven_triggered = deal.position_id in self.trailing_breakeven.positions_with_breakeven
                
                self.logger.info(f"🎲 Cerrada: {result.upper()} | ${profit:.2f} | {strategy.upper()}")
                
                if strategy in self.strategy_stats_tracker:
                    self.update_strategy_stat(strategy, profit, result)
                
                self.memory.update_trade_result(
                    trade_id=trade_info["trade_id"],
                    result=result,
                    profit=profit,
                    duration_minutes=duration,
                    trailing_triggered=trailing_triggered,
                    breakeven_triggered=breakeven_triggered
                )

                if profit >= MIN_PROFIT_FOR_AUTONOMY:
                    became_autonomous = self.ml_optimizer.update_operation_count(profit)
                    
                    if became_autonomous:
                        self.logger.success("🤖🤖🤖 SISTEMA AUTÓNOMO ACTIVADO 🤖🤖🤖")
                        self.logger.info("🧠 ML ahora optimizará parámetros automáticamente")
                        self.send_autonomy_data()
                
                if strategy == "ml":
                    correct = (
                        (trade_info["signal"] == 1 and result == "win") or
                        (trade_info["signal"] == -1 and result == "win")
                    )
                    
                    model_name = self.ensemble.active_model
                    if model_name in self.ensemble.models:
                        perf = self.ensemble.models[model_name]["performance"]
                        perf["trades"] += 1
                        
                        if correct:
                            perf["accuracy"] = ((perf["accuracy"] * (perf["trades"] - 1)) + 100) / perf["trades"]
                        else:
                            perf["accuracy"] = (perf["accuracy"] * (perf["trades"] - 1)) / perf["trades"]
                        
                        perf["profit"] += profit
                        
                        if perf["trades"] >= 5:
                            if perf["accuracy"] > 60:
                                self.ensemble.models[model_name]["weight"] = 1.5
                            elif perf["accuracy"] > 50:
                                self.ensemble.models[model_name]["weight"] = 1.0
                            else:
                                self.ensemble.models[model_name]["weight"] = 0.5
                
                self.ensemble.rotation_config["global_operations_count"] += 1
                
                rotation_status = self.ensemble.get_rotation_status()
                ops_until = rotation_status['operations_until_rotation']
                
                self.logger.info(f"   📚 Operación {self.ensemble.rotation_config['global_operations_count']} | Rotación ML en {ops_until} ops")
                
                if self.ensemble.should_rotate_cyclic():
                    rotation_event = self.ensemble.rotate_to_next_model()
                    
                    if rotation_event:
                        self.logger.info("")
                        self.logger.success("🔄🔄🔄 ROTACIÓN AUTOMÁTICA DE MODELO ML 🔄🔄🔄")
                        self.logger.info(f"   De: {rotation_event['from_model'].upper()}")
                        self.logger.info(f"   A:  {rotation_event['to_model'].upper()}")
                        self.logger.info(f"   Razón: {rotation_event['reason']}")
                        self.logger.info(f"   📚 Modelo anterior: {rotation_event['old_accuracy']:.1f}% ({rotation_event['old_trades']} ops)")
                        self.logger.info(f"   📚 Modelo nuevo: {rotation_event['new_accuracy']:.1f}% ({rotation_event['new_trades']} ops)")
                        self.logger.info(f"   ✅ Rotación completada después de {rotation_event['operations_completed']} operaciones")
                        self.logger.info("")
                
                if self.incremental_learning.should_retrain():
                    self.logger.info("🔄 Re-entrenamiento incremental iniciado...")
                    
                    df = self.get_historical_data(bars=3000)
                    if df is not None:
                        df = self.create_features(df)
                        df = self.create_target(df)
                        df.dropna(inplace=True)
                        
                        retrain_result = self.incremental_learning.incremental_train(df)
                        
                        if retrain_result:
                            self.logger.success(f"   ✅ Modelos actualizados (Operación #{self.incremental_learning.learning_stats['incremental_trains']})")
                            self.send_ml_status()
                
                self.ensemble.save_models()
                
                self.closed_trades_history[deal.position_id] = trade_info.copy()
                
                if len(self.closed_trades_history) > 100:
                    oldest_keys = sorted(self.closed_trades_history.keys())[:50]
                    for key in oldest_keys:
                        del self.closed_trades_history[key]
                
                self.trailing_breakeven.cleanup_closed_position(deal.position_id)
                
                del self.active_trades[deal.position_id]
            self.send_strategy_stats()

    def run(self, train_first=True):
        """
        🎖️ v6.0.1: Loop principal del bot con MEJORAS AVANZADAS
        
        PROCESO MEJORADO:
        1. Verificar filtro de noticias económicas
        2. Verificar estado de equity (drawdown crítico)
        3. Recolectar señales de todas las estrategias
        4. Validar señales con ML
        5. Ajustar confianza según equity
        6. 🔧 COOLDOWN GLOBAL: Filtrar señales en cooldown
        7. Filtrar y priorizar (MTF, límites)
        8. Verificar correlación
        9. Ejecutar señales aprobadas
        10. 🔧 REGISTRAR operaciones en cooldown
        """
        
        if not self.is_connected:
            if not self.connect():
                return
        
        if train_first:
            self.logger.info("=== ENTRENANDO MODELOS ML v6.0.1 ===")
            historical_data = self.get_historical_data(bars=2000)
            if historical_data is not None:
                df = self.create_features(historical_data)
                df = self.create_target(df)
                df.dropna(inplace=True)
                
                feature_columns = ['ema_21', 'ema_50', 'atr', 'adx', 'rsi', 'macd',
                                  'macd_signal', 'momentum', 'price_to_ema21',
                                  'price_to_ema50', 'ema_diff', 'bb_position', 'volume_change']
                
                X = df[feature_columns]
                y = df['target']
                
                from sklearn.model_selection import train_test_split
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                results = self.ensemble.train_all_models(X_train, y_train, X_test, y_test)
                
                for name, metrics in results.items():
                    if "error" not in metrics:
                        self.logger.success(f"✅ {name}: {metrics['test_accuracy']:.2%}")
        
        self.logger.info(f"🎯 {self.symbol} | TF: M30+MTF | Lote: {self.lot_size} | Max: {self.max_total_positions}")
        self.logger.info(f"🎖️ v6.0.1: COOLDOWN GLOBAL + MEJORAS AVANZADAS ACTIVAS")
        
        last_signal_check = datetime.now()
        last_mtf_update_fast = datetime.now()
        last_mtf_update_slow = datetime.now()
        last_day = datetime.now().day
        iteration = 0
        
        self.trailing_breakeven.update_params(self.ml_optimizer.initial_params)
        
        if self.mtf_enabled:
            mtf_summary = self.mtf_analyzer.get_detailed_summary()
            self.logger.info(mtf_summary)
        
        try:
            while True:
                iteration += 1
                current_time = datetime.now()
                
                if current_time.day != last_day:
                    last_day = current_time.day
                    self.daily_profit = 0.0
                    self.trading_enabled = True
                    self.logger.info("🌅 Nuevo día - Límites reseteados")
                
                try:
                    msg = self.gui_queue.get_nowait()
                    msg_type = msg.get('type')
                    
                    if msg_type == 'config':
                        self.update_config(
                            msg['max_profit'],
                            msg['max_loss'],
                            msg['lot_size'],
                            msg.get('max_positions', 10)
                        )
                    elif msg_type == 'reset_trading':
                        self.reset_trading_manual()
                    elif msg_type == 'strategy_config':
                        self.update_strategy_config(msg)
                    elif msg_type == 'request_autonomy_data':
                        self.send_autonomy_data()
                    elif msg_type == 'reset_autonomy':
                        self.reset_autonomy()
                        
                except:
                    pass
                
                self.check_positions()
                
                if iteration % 5 == 0:
                    daily_balance = self.calculate_daily_profit()
                    self.send_to_gui('daily_balance', balance=daily_balance)
                    self.check_daily_limits()
                    self.send_profit_charts_data()
                
                if self.mtf_enabled and (current_time - last_mtf_update_fast).total_seconds() >= 60:
                    if 'M30' in self.mtf_analyzer.timeframes:
                        self.mtf_analyzer.timeframes['M30']['last_update'] = None
                    if 'H1' in self.mtf_analyzer.timeframes:
                        self.mtf_analyzer.timeframes['H1']['last_update'] = None
                    
                    last_mtf_update_fast = current_time
                
                if self.mtf_enabled and (current_time - last_mtf_update_slow).total_seconds() >= 300:
                    for tf_name in ['H4', 'D1', 'W1']:
                        if tf_name in self.mtf_analyzer.timeframes:
                            self.mtf_analyzer.timeframes[tf_name]['last_update'] = None
                    
                    mtf_summary = self.mtf_analyzer.get_detailed_summary()
                    self.logger.info(mtf_summary)
                    
                    last_mtf_update_slow = current_time
                
                if (current_time - last_signal_check).total_seconds() >= 30:
                    
                    # 🎖️ PASO 1: VERIFICAR FILTRO DE NOTICIAS
                    is_safe, news_reason = self.news_filter.is_safe_to_trade()
                    if not is_safe:
                        self.logger.warning(news_reason)
                        self.logger.warning("📰 Trading pausado temporalmente")
                        last_signal_check = current_time
                        continue
                    
                    df = self.get_historical_data(bars=200)
                    if df is None:
                        time.sleep(1)
                        continue
                    
                    df = self.create_features(df)
                    features = self.prepare_features_for_prediction(df)
                    market_state = self.get_market_state(df)
                    
                    # Guardar market_state para trailing dinámico
                    self.market_state = market_state
                    
                    tick = mt5.symbol_info_tick(self.symbol)
                    current_price = tick.bid if tick else 0
                    
                    if iteration % 20 == 0:
                        self.logger.info(f"📊 Mercado: {market_state['trend']} | RSI:{market_state['rsi']:.0f} | ATR:{market_state['atr']:.2f}")
                    
                    # 🎖️ PASO 2: VERIFICAR EQUITY MONITOR
                    allow_trade, equity_reason = self.equity_monitor.should_allow_trade()
                    
                    # PASO 3: RECOLECTAR SEÑALES
                    all_signals = self.signal_aggregator.collect_all_signals(
                        df,
                        current_price,
                        market_state,
                        features
                    )
                    
                    if all_signals:
                        self.logger.info(f"📡 {len(all_signals)} señal(es) detectada(s):")
                        for sig in all_signals:
                            self.logger.info(f"   • {sig['strategy'].upper()}: {sig['reason']}")
                    
                    # 🎖️ PASO 4: VALIDAR SEÑALES CON ML
                    if all_signals and self.ml_validator.enabled:
                        self.logger.info(f"🧠 Validando señales con ML Validator...")
                        all_signals = self.ml_validator.batch_validate_signals(all_signals, features)
                    
                    # 🎖️ PASO 5: AJUSTAR CONFIANZA POR EQUITY
                    confidence_adjustment = self.equity_monitor.get_confidence_adjustment()
                    
                    if confidence_adjustment != 0.0:
                        mode = self.equity_monitor.determine_trading_mode()
                        self.logger.info(f"💰 Ajustando confianza por equity ({mode}): {confidence_adjustment:+.0%}")
                        
                        for sig in all_signals:
                            original_conf = sig['confidence']
                            sig['confidence'] = max(0.25, min(sig['confidence'] + confidence_adjustment, 0.95))
                            
                            if abs(sig['confidence'] - original_conf) > 0.01:
                                self.logger.info(f"   • {sig['strategy'].upper()}: {original_conf:.2f} → {sig['confidence']:.2f}")
                    
                    if not self.trading_enabled:
                        if all_signals:
                            self.logger.warning("🛑 Trading deshabilitado - Señales ignoradas")
                        last_signal_check = current_time
                        continue
                    
                    positions = mt5.positions_get(symbol=self.symbol)
                    positions = positions if positions else []
                    
                    if all_signals:
                        self.logger.info(f"📊 Posiciones abiertas: {len(positions)}/{self.max_total_positions}")
                    
                    # 🔧 PASO 6: FILTRAR CON COOLDOWN GLOBAL + MTF + LÍMITES
                    # (El cooldown se aplica dentro de filter_and_prioritize)
                    final_signals = self.signal_aggregator.filter_and_prioritize(
                        all_signals,
                        positions,
                        self.active_trades,
                        self.max_total_positions
                    )
                    
                    if all_signals and not final_signals:
                        signals_blocked_by_mtf = [s for s in all_signals if s.get('mtf_status') == 'blocked']
                        
                        if signals_blocked_by_mtf:
                            self.logger.warning(f"⛔ {len(signals_blocked_by_mtf)} señal(es) BLOQUEADAS por MTF:")
                            for sig in signals_blocked_by_mtf:
                                direction = "BUY" if sig['signal'] == 1 else "SELL"
                                self.logger.info(f"   • {sig['strategy'].upper()} {direction}: {sig.get('mtf_reason', 'Sin alineación MTF')}")
                        else:
                            self.logger.warning(f"⚠️ {len(all_signals)} señales filtradas (cooldown/límites alcanzados)")
                    
                    # 🎖️ PASO 7: VERIFICAR CORRELACIÓN
                    if final_signals:
                        approved_signals = []
                        
                        account_info = mt5.account_info()
                        account_balance = account_info.balance if account_info else 10000.0
                        
                        for signal in final_signals:
                            allowed, corr_reason = self.correlation_manager.check_signal_correlation(
                                signal,
                                positions,
                                self.active_trades,
                                account_balance
                            )
                            
                            if allowed:
                                approved_signals.append(signal)
                            else:
                                signal_dir = "BUY" if signal['signal'] == 1 else "SELL"
                                self.logger.warning(f"🛑 Correlación bloqueó {signal['strategy'].upper()} {signal_dir}")
                                self.logger.warning(f"   Razón: {corr_reason}")
                        
                        final_signals = approved_signals
                    
                    # 🔧 PASO 8: EJECUTAR SEÑALES APROBADAS
                    # (El registro en cooldown se hace dentro de open_trade_from_signal)
                    if final_signals:
                        self.logger.success(f"🏆 {len(final_signals)} señal(es) APROBADA(s) para ejecutar")
                        
                        for sig in final_signals:
                            if sig.get('mtf_status') == 'approved':
                                self.logger.info(f"   ✔️ {sig.get('mtf_reason', 'MTF aprobado')}")
                        
                        for signal in final_signals:
                            try:
                                success = self.open_trade_from_signal(
                                    signal_data=signal,
                                    features=features,
                                    market_state=market_state,
                                    df=df
                                )
                                
                                if success:
                                    self.logger.success(f"✔️ Operación ejecutada: {signal['strategy'].upper()}")
                                    # 🔧 El registro en cooldown ya se hizo dentro de open_trade_from_signal
                                else:
                                    self.logger.warning(f"⚠️ Fallo al ejecutar: {signal['strategy'].upper()}")
                                    
                            except Exception as e:
                                self.logger.error(f"❌ Error ejecutando señal: {e}")
                    
                    self.send_signal_stats()
                    last_signal_check = current_time
                
                if iteration % 10 == 0:
                    self.check_and_close_trades()
                
                if iteration % 30 == 0:
                    self.send_ml_status()
                
                if iteration % 20 == 0:
                    self.send_autonomy_data()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.warning("🛑Bot detenido")
            self.disconnect()


def run_bot_with_ml_gui():
    """Ejecuta bot v6.0.1 CON COOLDOWN GLOBAL CORREGIDO"""
    
    root = tk.Tk()
    gui = EnhancedTradingBotGUI(root)
    
    bot = MLTradingBot(gui_queue=gui.message_queue)
    
    def run_bot_thread():
        bot.run(train_first=True)
    
    bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    
    root.mainloop()
    
    bot.disconnect()


if __name__ == "__main__":
    print("="*80)
    print("🤖 BOT DE TRADING XAUUSD - ML v6.0.1 COOLDOWN GLOBAL CORREGIDO")
    print("🚀 INICIANDO BOT v6.0.1")
    print()
    
    run_bot_with_ml_gui()
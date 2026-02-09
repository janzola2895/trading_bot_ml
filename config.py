"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    CONFIGURACIÓN GLOBAL DEL BOT v6.0                     ║
║                                                                          ║
║  🆕 v6.0: SL/TP Dinámico + Validación ML + Correlación + Equity         ║
║  🆕 MTF SIMPLIFICADO: W1 (dirección) + H1/H4 (confirmación)             ║
║  Configuraciones centralizadas para el bot de trading                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import MetaTrader5 as mt5

# ============================================================================
# CREDENCIALES MT5
# ============================================================================

MT5_ACCOUNT = 40890095
MT5_PASSWORD = "Camilo952800."
MT5_SERVER = "Deriv-Demo"

# ============================================================================
# CONFIGURACIÓN DE TRADING
# ============================================================================

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M30
MAGIC_NUMBER = 999888

# Límites de trading
DEFAULT_LOT_SIZE = 0.02
DEFAULT_MAX_DAILY_PROFIT = 1000.0
DEFAULT_MAX_DAILY_LOSS = 5000.0
DEFAULT_MAX_POSITIONS = 10

# ============================================================================
# 🆕 v6.0 - FASE 1: SL/TP DINÁMICO
# ============================================================================

# Activar/desactivar SL/TP dinámico
USE_DYNAMIC_SLTP = True

# Multiplicadores ATR base
ATR_MULTIPLIER_SL = 2.0    # SL = ATR * 2.0
ATR_MULTIPLIER_TP = 4.0    # TP = ATR * 4.0

# Ajustes según volatilidad
VOLATILITY_THRESHOLDS = {
    'low': 1.5,     # ATR < 1.5 = baja volatilidad
    'high': 3.0     # ATR > 3.0 = alta volatilidad
}

VOLATILITY_ADJUSTMENTS = {
    'low': {
        'sl_multiplier': 1.5,  # Menos espacio en baja volatilidad
        'tp_multiplier': 3.0
    },
    'normal': {
        'sl_multiplier': 2.0,
        'tp_multiplier': 4.0
    },
    'high': {
        'sl_multiplier': 2.5,  # Más espacio en alta volatilidad
        'tp_multiplier': 5.0
    }
}

# Ajustes según tendencia
TREND_ADJUSTMENTS = {
    'uptrend': {
        'buy_tp_bonus': 1.2,    # TP más amplio en BUY con tendencia alcista
        'sell_sl_tighter': 0.9  # SL más ajustado en SELL contra tendencia
    },
    'downtrend': {
        'sell_tp_bonus': 1.2,   # TP más amplio en SELL con tendencia bajista
        'buy_sl_tighter': 0.9   # SL más ajustado en BUY contra tendencia
    },
    'sideways': {
        'tp_reduction': 0.85,   # TP más conservador en rango
        'sl_reduction': 0.95
    }
}

# Límites de seguridad (en pips)
MIN_SL_PIPS = 20
MAX_SL_PIPS = 150
MIN_TP_PIPS = 30
MAX_TP_PIPS = 300
MIN_RISK_REWARD_RATIO = 1.5  # TP debe ser al menos 1.5x el SL

# ============================================================================
# 🆕 v6.0 - FASE 2: VALIDACIÓN ML DE SEÑALES
# ============================================================================

# Activar validación ML
USE_ML_SIGNAL_VALIDATION = True

# Umbrales de confianza ML
ML_CONFIDENCE_THRESHOLD_BOOST = 0.75  # Señales >75% reciben boost
ML_CONFIDENCE_THRESHOLD_PENALTY = 0.50  # Señales <50% reciben penalización

# Ajustes de confianza
ML_CONFIDENCE_BOOST_AMOUNT = 0.10  # +10% confianza para señales fuertes
ML_CONFIDENCE_PENALTY_AMOUNT = 0.15  # -15% confianza para señales débiles

# Bloqueo de señales débiles
BLOCK_WEAK_ML_SIGNALS = True  # Bloquear si confianza ML < 40%
ML_MINIMUM_CONFIDENCE = 0.40

# Win rate histórico para validación
ML_MIN_WINRATE_FOR_BOOST = 55.0  # Win rate >55% habilita boost
ML_WINRATE_CHECK_LAST_N_TRADES = 20  # Verificar últimas 20 ops

# ============================================================================
# 🆕 v6.0 - FASE 3: GESTIÓN DE CORRELACIÓN
# ============================================================================

# Activar gestión de correlación
USE_CORRELATION_MANAGEMENT = True

# Límite máximo de posiciones correlacionadas
MAX_CORRELATED_POSITIONS = 2  # Máximo 2 posiciones de la misma dirección

# Período de análisis (minutos)
CORRELATION_ANALYSIS_PERIOD = 120  # Últimas 2 horas

# Cooldown entre operaciones correlacionadas (minutos)
CORRELATION_COOLDOWN_MINUTES = 30  # Esperar 30 min antes de otra operación similar

# ============================================================================
# 🆕 v6.0 - FASE 4: MONITOREO DE EQUITY Y DRAWDOWN
# ============================================================================

# Activar monitoreo de equity
USE_EQUITY_MONITORING = True

# Umbrales de drawdown
DRAWDOWN_WARNING_THRESHOLD = 50.0   # Advertencia al 15%
DRAWDOWN_CRITICAL_THRESHOLD = 75.0  # Crítico al 25%
DRAWDOWN_STOP_THRESHOLD = 80.0      # Detener trading al 35%

# Ajustes según drawdown
DRAWDOWN_ADJUSTMENTS = {
    'normal': {  # 0-15%
        'lot_multiplier': 1.0,
        'confidence_adjustment': 0.0,
        'max_positions_adjustment': 1.0
    },
    'warning': {  # 15-25%
        'lot_multiplier': 0.75,  # Reducir lotes a 75%
        'confidence_adjustment': 0.05,  # Requiere +5% confianza
        'max_positions_adjustment': 0.75  # 75% de posiciones máximas
    },
    'critical': {  # 25-35%
        'lot_multiplier': 0.50,  # Reducir lotes a 50%
        'confidence_adjustment': 0.10,  # Requiere +10% confianza
        'max_positions_adjustment': 0.50  # 50% de posiciones máximas
    }
}

# Balance inicial (actualizar con tu balance real)
INITIAL_BALANCE = 10000.0  # USD

# ============================================================================
# 🆕 v6.0 - FASE 5: FILTRO DE NOTICIAS ECONÓMICAS
# ============================================================================

# Activar filtro de noticias
USE_NEWS_FILTER = False  # Desactivado por defecto (requiere API key)

# API de noticias (ForexFactory, Investing.com, etc.)
NEWS_API_KEY = ""  # Agregar tu API key aquí
NEWS_API_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Impacto de noticias para bloquear trading
NEWS_BLOCK_IMPACTS = ['HIGH']  # Bloquear solo en noticias de ALTO impacto

# Minutos antes/después de noticia para bloquear
NEWS_BLOCK_BEFORE_MINUTES = 15  # 15 min antes
NEWS_BLOCK_AFTER_MINUTES = 15   # 15 min después

# Monedas a monitorear (para XAUUSD principalmente USD)
NEWS_MONITOR_CURRENCIES = ['USD', 'EUR', 'GBP']

# ============================================================================
# CONFIGURACIÓN DE APRENDIZAJE ML
# ============================================================================

# 🆕 Profit mínimo para contar operación hacia autonomía (configurable desde GUI)
MIN_PROFIT_FOR_AUTONOMY = 5.0  # USD - Solo ops ganadoras >= $5

# Profit mínimo para re-entrenamiento incremental
MIN_PROFIT_FOR_LEARNING = 10.0  # USD

# Número de operaciones ganadoras necesarias para activar autonomía
AUTONOMY_THRESHOLD = 100

# Re-entrenamiento incremental cada N operaciones
RETRAIN_EVERY_N_OPS = 10

# Rotación de modelos ML cada N operaciones (TODAS las estrategias)
ROTATE_MODELS_EVERY_N_OPS = 10

# ============================================================================
# CONFIGURACIÓN DE VALIDACIÓN DE ÓRDENES
# ============================================================================

# Spread máximo permitido (pips)
MAX_SPREAD_PIPS = 50

# Sistema de retry
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# Modificaciones SL/TP
MODIFICATION_COOLDOWN_SECONDS = 5
MIN_DISTANCE_FROM_PRICE_PIPS = 10

# Cache de información del símbolo
SYMBOL_CACHE_SECONDS = 60

# ============================================================================
# CONFIGURACIÓN DE ESTRATEGIAS
# ============================================================================

# Support/Resistance
SR_LOOKBACK_BARS = 100
SR_MIN_TOUCHES = 3
SR_TOLERANCE_PIPS = 20

# Fibonacci
FIBO_SWING_LOOKBACK = 50
FIBO_MIN_SWING_PIPS = 100

# Price Action
PA_MIN_CANDLE_BODY_PIPS = 10
PA_MAX_WICK_RATIO = 3.0

# Candlestick
CS_MIN_BODY_PIPS = 12
CS_MIN_CONFIDENCE = 0.60
CS_MIN_ENGULF_RATIO = 1.8
CS_REQUIRE_TREND_CONTEXT = True
CS_VOLUME_CONFIRMATION = False

# 🆕 v5.2.4: Sistema de Cooldown Anti-Consecutivas
CS_COOLDOWN_AFTER_SIGNAL_MINUTES = 60
CS_MIN_CANDLES_BETWEEN_SIGNALS = 2

# Liquidity
LIQ_LOOKBACK_BARS = 30
LIQ_SWEEP_TOLERANCE_PIPS = 15
LIQ_MIN_WICK_SIZE_PIPS = 1000
LIQ_MIN_DISTANCE_FROM_SWEEP_PIPS = 100

# ============================================================================
# 🆕 CONFIGURACIÓN MULTI-TIMEFRAME (MTF) SIMPLIFICADO
# ============================================================================

MTF_ENABLED_DEFAULT = False

# 🆕 SISTEMA SIMPLIFICADO: Solo 3 timeframes
# - W1: Define la DIRECCIÓN PRINCIPAL del mercado
# - H1 y H4: Proveen CONFIRMACIÓN de la dirección
MTF_TIMEFRAMES = {
    'H1': {
        'tf': mt5.TIMEFRAME_H1,
        'priority': 'confirmation',  # Timeframe de confirmación
        'update_interval': 60,
    },
    'H4': {
        'tf': mt5.TIMEFRAME_H4,
        'priority': 'confirmation',  # Timeframe de confirmación
        'update_interval': 300,
    },
    'W1': {
        'tf': mt5.TIMEFRAME_W1,
        'priority': 'master',  # Timeframe MAESTRO (define dirección)
        'update_interval': 300,
    }
}

# 🆕 NUEVA LÓGICA MTF SIMPLIFICADA
# Regla: W1 define dirección + necesita 1 de 2 confirmaciones (H1 o H4)
MTF_REQUIRES_W1_DIRECTION = True  # W1 es obligatorio para definir dirección
MTF_REQUIRES_CONFIRMATION = True  # Necesita al menos 1 confirmación (H1 o H4)

# ============================================================================
# CONFIGURACIÓN DE TRAILING STOP Y BREAKEVEN
# ============================================================================

# Trailing Stop (valores iniciales, ML puede optimizar)
TRAILING_ENABLED = True
TRAILING_ACTIVATION_PIPS = 30
TRAILING_DISTANCE_PIPS = 20

# 🆕 v6.0: Trailing dinámico basado en ATR
TRAILING_USE_ATR = True
TRAILING_ATR_MULTIPLIER = 1.5  # Distancia = ATR * 1.5

# Breakeven (valores iniciales, ML puede optimizar)
BREAKEVEN_ENABLED = True
BREAKEVEN_ACTIVATION_PIPS = 40
BREAKEVEN_SAFETY_PIPS = 5

# ============================================================================
# CONFIGURACIÓN DE LÍMITES POR ESTRATEGIA
# ============================================================================

MAX_POSITIONS_PER_STRATEGY = {
    'ml': 2,
    'sr': 2,
    'fibo': 2,
    'price_action': 2,
    'candlestick': 1,
    'liquidity': 3
}

# ============================================================================
# CONFIGURACIÓN DE FILTROS DE CALIDAD
# ============================================================================

QUALITY_FILTERS = {
    'ml': {
        'min_confidence': 0.70,
        'require_trend': False
    },
    'sr': {
        'min_confidence': 0.65,
        'min_touches': 3,
        'require_volume': False
    },
    'fibo': {
        'min_confidence': 0.60,
        'min_level': 0.618,
        'require_trend': True
    },
    'price_action': {
        'min_confidence': 0.65,
        'require_trend_confirm': True
    },
    'candlestick': {
        'min_confidence': 0.65,
        'require_trend_confirm': False
    },
    'liquidity': {
        'min_confidence': 0.75,
        'prefer_sweeps': True
    }
}

# ============================================================================
# CONFIGURACIÓN DE DATOS
# ============================================================================

DATA_DIR = "bot_data"
MODELS_DIR = "bot_data/models"

# ============================================================================
# CONFIGURACIÓN DE GUI
# ============================================================================

WINDOW_WIDTH = 1700
WINDOW_HEIGHT = 950

# Colores del tema
THEME_COLORS = {
    'bg_primary': '#1e1e1e',
    'bg_secondary': '#2d2d2d',
    'fg_primary': '#ffffff',
    'fg_success': '#44ff44',
    'fg_warning': '#ffaa00',
    'fg_error': '#ff4444',
    'fg_info': '#00aaff',
    'accent': '#00ff00'
}

# Actualización de GUI (milisegundos)
GUI_UPDATE_INTERVAL = 100

# Actualización de gráficas (milisegundos)
CHARTS_UPDATE_INTERVAL = 5000

# ============================================================================
# CONFIGURACIÓN DE LOGS
# ============================================================================

LOG_MAX_LINES = 50
LOG_TO_FILE = False
LOG_FILE_PATH = "bot_data/trading_bot.log"

# ============================================================================
# CONFIGURACIÓN DE MODELO ML
# ============================================================================

# Random Forest
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 12
RF_MIN_SAMPLES_SPLIT = 20

# Gradient Boosting
GB_N_ESTIMATORS = 150
GB_MAX_DEPTH = 8
GB_LEARNING_RATE = 0.1

# Neural Network
NN_HIDDEN_LAYERS = (100, 50, 25)
NN_ACTIVATION = 'relu'
NN_MAX_ITER = 500

# ============================================================================
# CONFIGURACIÓN DE INDICADORES TÉCNICOS
# ============================================================================

# EMAs
EMA_PERIODS = {
    'fast': 21,
    'medium': 50,
    'slow': 100
}

# Otros indicadores
ATR_PERIOD = 14
ADX_PERIOD = 14
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# ============================================================================
# CONFIGURACIÓN DE BARRAS HISTÓRICAS
# ============================================================================

BARS_FOR_FEATURES = 200
BARS_FOR_TRAINING = 2000
BARS_FOR_PREDICTION = 100

STRATEGY_RISK_PROFILES = {
    'ml': {
        'sl_type': 'atr_based',  # Basado en ATR (volatilidad)
        'sl_atr_multiplier': 1.5,
        'tp_atr_multiplier': 3.5,
        'min_sl_pips': 40,
        'max_sl_pips': 100,
        'risk_reward': 2.3,
        'description': 'ML adapta a volatilidad actual'
    },
    'sr': {
        'sl_type': 'dynamic',  # Dinámico según distancia a niveles
        'sl_pips': 40,
        'tp_pips': 100,
        'max_sl_pips': 80,
        'risk_reward': 2.5,
        'description': 'S/R ajusta según fuerza del nivel'
    },
    'fibo': {
        'sl_type': 'fixed',  # Fijo conservador
        'sl_pips': 40,
        'tp_pips': 100,
        'risk_reward': 2.5,
        'description': 'Fibonacci usa SL/TP fijos conservadores'
    },
    'price_action': {
        'sl_type': 'pattern_based',  # Basado en tamaño del patrón
        'sl_multiplier': 1.2,  # SL = tamaño_patrón * 1.2
        'tp_multiplier': 3.0,  # TP = tamaño_patrón * 3.0
        'min_sl_pips': 60,
        'max_sl_pips': 70,
        'risk_reward': 2.5,
        'description': 'PA ajusta según tamaño de vela'
    },
    'candlestick': {
        'sl_type': 'tight',  # Tight para reversiones
        'sl_pips': 50,
        'tp_pips': 100,
        'use_pattern_size': True,
        'risk_reward': 2.4,
        'description': 'Candlestick usa SL/TP tight'
    },
    'liquidity': {
        'sl_type': 'zone_based',  # Basado en tamaño de zona
        'sl_pips': 45,
        'tp_pips': 110,
        'zone_buffer_pips': 10,
        'risk_reward': 2.4,
        'description': 'Liquidez usa zona + buffer'
    }
}

# ============================================================================
# 🆕 v6.0 - LÍMITES DE SEGURIDAD SL/TP
# ============================================================================

MIN_SL_PIPS = 20
MAX_SL_PIPS = 150
MIN_TP_PIPS = 30
MAX_TP_PIPS = 300
MIN_RISK_REWARD_RATIO = 1.5  # TP debe ser al menos 1.5x el SL
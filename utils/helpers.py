"""
╔══════════════════════════════════════════════════════════════════════════╗
║                     FUNCIONES AUXILIARES v5.2                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime


def format_timestamp(timestamp):
    """Formatea timestamp a string legible"""
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp)
    else:
        dt = timestamp
    
    return dt.strftime("%H:%M:%S")


def format_profit(profit):
    """Formatea profit con símbolo y color"""
    if profit > 0:
        return f"💚 ${profit:.2f}"
    elif profit < 0:
        return f"❤️ ${profit:.2f}"
    else:
        return f"${profit:.2f}"


def pips_to_price(pips, point=0.01):
    """Convierte pips a precio"""
    return pips * point * 10


def price_to_pips(price_diff, point=0.01):
    """Convierte diferencia de precio a pips"""
    return price_diff / (point * 10)


def normalize_volume(volume, volume_min, volume_max, volume_step):
    """Normaliza volumen según límites del símbolo"""
    # Verificar límites
    if volume < volume_min:
        volume = volume_min
    elif volume > volume_max:
        volume = volume_max
    
    # Normalizar al step correcto
    normalized = round(volume / volume_step) * volume_step
    normalized = round(normalized, 2)
    
    return normalized


def extract_strategy_from_comment(comment):
    """Extrae estrategia del comment de MT5"""
    if not comment:
        return "unknown"
    
    # Formato: "ESTRATEGIA-v5.2-intento"
    parts = comment.split("-")
    if len(parts) >= 1:
        strategy = parts[0].lower()
        if strategy in ['ml', 'sr', 'fibo', 'price_action', 'candlestick', 'liquidity']:
            return strategy
    
    return "unknown"
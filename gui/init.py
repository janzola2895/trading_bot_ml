"""
Interfaz gráfica del bot de trading

🆕 MODIFICADO: Agregar import de ChartsWindow
"""

from .main_window import EnhancedTradingBotGUI
from .ml_dashboard import MLDashboardPanel
from .strategies_panel import StrategiesControlPanel
from .autonomy_window import MLAutonomyWindow
from .charts_window import ChartsWindow  # 🆕 NUEVO
from .charts import ChartManager

__all__ = [
    'EnhancedTradingBotGUI',
    'MLDashboardPanel',
    'StrategiesControlPanel',
    'MLAutonomyWindow',
    'ChartsWindow',  # 🆕 NUEVO
    'ChartManager'
]
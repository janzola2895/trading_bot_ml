# GUI Package
"""
Interfaz gráfica del bot de trading

🆕 MODIFICADO: Agregar import de StrategyChartWindow
"""

from .main_window import EnhancedTradingBotGUI
from .ml_dashboard import MLDashboardPanel
from .strategies_panel import StrategiesControlPanel
from .autonomy_window import MLAutonomyWindow
from .charts_window import ChartsWindow
from .strategy_chart_window import StrategyChartWindow
from .charts import ChartManager

__all__ = [
    'EnhancedTradingBotGUI',
    'MLDashboardPanel',
    'StrategiesControlPanel',
    'MLAutonomyWindow',
    'ChartsWindow',
    'StrategyChartWindow',
    'ChartManager'
]
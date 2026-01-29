"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    SISTEMA DE GRÁFICAS v5.2                              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class ChartManager:
    """Gestor de gráficas de profit"""
    
    def __init__(self, hourly_parent=None, daily_parent=None):
        """
        Args:
            hourly_parent: Frame para la gráfica horaria
            daily_parent: Frame para la gráfica diaria
        """
        self.hourly_parent = hourly_parent
        self.daily_parent = daily_parent
        
        # Datos
        self.hourly_profits = [0] * 24
        self.daily_profits = [0] * 31
        
        # Solo crear gráficas si se proporcionan los parents
        if hourly_parent and daily_parent:
            self.setup_charts()
        else:
            self.hourly_canvas = None
            self.daily_canvas = None
    
    def setup_charts(self):
        """Configura las gráficas"""
        
        # GRÁFICA HORARIA
        self.hourly_fig = Figure(figsize=(3.75, 2.25), dpi=80, facecolor='#2d2d2d')
        self.hourly_ax = self.hourly_fig.add_subplot(111)
        self.hourly_ax.set_facecolor('#1e1e1e')
        self.hourly_ax.set_xlabel('Hora', color='white', fontsize=8)
        self.hourly_ax.set_ylabel('Profit ($)', color='white', fontsize=8)
        self.hourly_ax.tick_params(colors='white', labelsize=7)
        self.hourly_ax.grid(True, alpha=0.2, color='white')
        self.hourly_fig.tight_layout()
        
        self.hourly_canvas = FigureCanvasTkAgg(self.hourly_fig, master=self.hourly_parent)
        self.hourly_canvas.draw()
        self.hourly_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # GRÁFICA DIARIA
        self.daily_fig = Figure(figsize=(3.75, 2.25), dpi=80, facecolor='#2d2d2d')
        self.daily_ax = self.daily_fig.add_subplot(111)
        self.daily_ax.set_facecolor('#1e1e1e')
        self.daily_ax.set_xlabel('Día del Mes', color='white', fontsize=8)
        self.daily_ax.set_ylabel('Profit ($)', color='white', fontsize=8)
        self.daily_ax.tick_params(colors='white', labelsize=7)
        self.daily_ax.grid(True, alpha=0.2, color='white')
        self.daily_fig.tight_layout()
        
        self.daily_canvas = FigureCanvasTkAgg(self.daily_fig, master=self.daily_parent)
        self.daily_canvas.draw()
        self.daily_canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def get_hourly_widget(self):
        """Retorna widget de gráfica horaria"""
        if self.hourly_canvas:
            return self.hourly_canvas.get_tk_widget()
        return None
    
    def get_daily_widget(self):
        """Retorna widget de gráfica diaria"""
        if self.daily_canvas:
            return self.daily_canvas.get_tk_widget()
        return None
    
    def update_hourly_chart(self, hours, profits):
        """Actualiza gráfica horaria con valores en puntos"""
        if not self.hourly_canvas:
            return
            
        self.hourly_ax.clear()
        self.hourly_ax.set_facecolor('#1e1e1e')
        
        last_hour_with_data = datetime.now().hour
        hours_to_plot = hours[:last_hour_with_data + 1]
        profits_to_plot = profits[:last_hour_with_data + 1]
        
        if len(hours_to_plot) > 0:
            self.hourly_ax.plot(hours_to_plot, profits_to_plot, color='#00aaff',
                               linewidth=2, marker='o', markersize=5)
            
            for h, p in zip(hours_to_plot, profits_to_plot):
                if p != 0:
                    color = '#44ff44' if p > 0 else '#ff4444'
                    self.hourly_ax.annotate(f'${p:.1f}',
                                           xy=(h, p), xytext=(0, 8),
                                           textcoords='offset points',
                                           ha='center', va='bottom',
                                           color=color, fontsize=7, fontweight='bold',
                                           bbox=dict(boxstyle='round,pad=0.2',
                                                   facecolor='#1e1e1e',
                                                   edgecolor=color, linewidth=1))
        
        self.hourly_ax.axhline(y=0, color='white', linestyle='--', alpha=0.5, linewidth=1)
        self.hourly_ax.set_xlabel('Hora del Día', color='white', fontsize=9)
        self.hourly_ax.set_ylabel('Profit ($)', color='white', fontsize=9)
        self.hourly_ax.set_title('Profit por Hora', color='#00ff00', fontsize=10, fontweight='bold')
        self.hourly_ax.tick_params(colors='white', labelsize=8)
        self.hourly_ax.grid(True, alpha=0.2, color='white', linestyle=':')
        self.hourly_ax.set_xlim(-0.5, 23.5)
        self.hourly_ax.set_xticks(range(0, 24, 2))
        
        self.hourly_fig.tight_layout()
        self.hourly_canvas.draw()
    
    def update_daily_chart(self, days, profits):
        """Actualiza gráfica diaria con valores en puntos"""
        if not self.daily_canvas:
            return
            
        self.daily_ax.clear()
        self.daily_ax.set_facecolor('#1e1e1e')
        
        last_day = datetime.now().day
        days_to_plot = [d for d in days if d <= last_day]
        profits_to_plot = [profits[i] for i, d in enumerate(days) if d <= last_day]
        
        if len(days_to_plot) > 0:
            self.daily_ax.plot(days_to_plot, profits_to_plot, color='#00ff88',
                              linewidth=2, marker='o', markersize=4)
            
            for d, p in zip(days_to_plot, profits_to_plot):
                if p != 0 and abs(p) > 10:
                    color = '#44ff44' if p > 0 else '#ff4444'
                    self.daily_ax.annotate(f'${p:.1f}',
                                          xy=(d, p), xytext=(0, 8),
                                          textcoords='offset points',
                                          ha='center', va='bottom',
                                          color=color, fontsize=7, fontweight='bold',
                                          bbox=dict(boxstyle='round,pad=0.2',
                                                  facecolor='#1e1e1e',
                                                  edgecolor=color, linewidth=1))
        
        self.daily_ax.axhline(y=0, color='white', linestyle='--', alpha=0.5, linewidth=1)
        self.daily_ax.set_xlabel('Día del Mes', color='white', fontsize=9)
        self.daily_ax.set_ylabel('Profit ($)', color='white', fontsize=9)
        self.daily_ax.set_title('Profit Acumulado por Día', color='#00ff00', fontsize=10, fontweight='bold')
        self.daily_ax.tick_params(colors='white', labelsize=8)
        self.daily_ax.grid(True, alpha=0.2, color='white', linestyle=':')
        self.daily_ax.set_xlim(0.5, 31.5)
        self.daily_ax.set_xticks(range(1, 32, 3))
        
        self.daily_fig.tight_layout()
        self.daily_canvas.draw()
    
    def update_data(self, hourly_data, daily_data):
        """Actualiza datos de las gráficas"""
        self.hourly_profits = hourly_data
        self.daily_profits = daily_data
        
        hours = list(range(24))
        self.update_hourly_chart(hours, self.hourly_profits)
        
        days = list(range(1, 32))
        self.update_daily_chart(days, self.daily_profits)
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   VENTANA DE GRÁFICAS DE PROFIT v5.2                     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from .charts import ChartManager


class ChartsWindow:
    """
    Ventana separada para mostrar gráficas de profit
    - Profit por hora (HOY)
    - Profit acumulado por día (MES)
    - Auto-actualización cada 30 segundos
    """
    
    def __init__(self, parent, bot_queue):
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Gráficas de Profit v5.2")
        self.window.geometry("1000x700")
        self.window.configure(bg="#1e1e1e")
        
        self.bot_queue = bot_queue
        self.chart_manager = None
        
        self.setup_ui()
        self.auto_update()
    
    def setup_ui(self):
        """Configura la interfaz de la ventana"""
        # HEADER
        header = tk.Frame(self.window, bg="#2d2d2d", height=60)
        header.pack(fill=tk.X, padx=10, pady=8)
        header.pack_propagate(False)
        
        title = tk.Label(header, text="📊 GRÁFICAS DE PROFIT",
                        font=("Arial", 16, "bold"), bg="#2d2d2d", fg="#00ff00")
        title.pack(pady=5)
        
        subtitle = tk.Label(header, text="Análisis visual del rendimiento del bot",
                           font=("Arial", 9), bg="#2d2d2d", fg="#aaaaaa")
        subtitle.pack()
        
        # CONTENEDOR PRINCIPAL
        main_container = tk.Frame(self.window, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # GRÁFICA HORARIA
        hourly_frame = tk.LabelFrame(main_container, 
                                     text="📊 PROFIT POR HORA (HOY)",
                                     font=("Arial", 11, "bold"), 
                                     bg="#2d2d2d",
                                     fg="#ffffff", 
                                     padx=10, 
                                     pady=10)
        hourly_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # GRÁFICA DIARIA
        daily_frame = tk.LabelFrame(main_container, 
                                    text="📈 PROFIT ACUMULADO POR DÍA (MES)",
                                    font=("Arial", 11, "bold"), 
                                    bg="#2d2d2d",
                                    fg="#ffffff", 
                                    padx=10, 
                                    pady=10)
        daily_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 🆕 CREAR ChartManager DESPUÉS de crear los frames y pasarlos como parámetros
        self.chart_manager = ChartManager(hourly_parent=hourly_frame, daily_parent=daily_frame)
        
        # CONTROLES
        controls_frame = tk.Frame(self.window, bg="#2d2d2d", height=50)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        controls_frame.pack_propagate(False)
        
        # Botón refrescar
        btn_refresh = tk.Button(controls_frame, 
                               text="🔄 Actualizar Ahora",
                               font=("Arial", 10, "bold"), 
                               bg="#44ff44", 
                               fg="#000000",
                               command=self.request_update, 
                               cursor="hand2", 
                               width=20)
        btn_refresh.pack(side=tk.LEFT, padx=10)
        
        # Checkbox auto-actualización
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(controls_frame, 
                                   text="Auto-actualizar cada 30s",
                                   variable=self.auto_update_var, 
                                   font=("Arial", 9),
                                   bg="#2d2d2d", 
                                   fg="#ffffff", 
                                   selectcolor="#1e1e1e")
        auto_check.pack(side=tk.LEFT, padx=10)
        
        # Label última actualización
        self.last_update_label = tk.Label(controls_frame, 
                                          text="Última actualización: --:--:--",
                                          font=("Arial", 9), 
                                          bg="#2d2d2d", 
                                          fg="#aaaaaa")
        self.last_update_label.pack(side=tk.RIGHT, padx=10)
    
    def request_update(self):
        """Solicita actualización de datos al bot"""
        if self.bot_queue:
            self.bot_queue.put({'type': 'request_profit_charts'})
            
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.config(text=f"Última actualización: {now}")
    
    def auto_update(self):
        """Auto-actualización cada 30 segundos"""
        if self.auto_update_var.get():
            self.request_update()
        
        # Programar siguiente actualización
        self.window.after(30000, self.auto_update)  # 30 segundos
    
    def update_charts(self, hourly_data, daily_data):
        """Actualiza las gráficas con nuevos datos"""
        if self.chart_manager:
            self.chart_manager.update_data(hourly_data, daily_data)
            
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.config(text=f"Última actualización: {now}")
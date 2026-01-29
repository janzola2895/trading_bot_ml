"""
╔══════════════════════════════════════════════════════════════════════════╗
║              PANEL DE CONTROL DE ESTRATEGIAS v5.2                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk


class StrategiesControlPanel:
    """Panel de control para activar/desactivar estrategias"""
    
    def __init__(self, parent, message_queue):
        self.message_queue = message_queue
        
        self.frame = tk.LabelFrame(parent, text="🎯 ESTRATEGIAS",
                                   font=("Arial", 10, "bold"), bg="#2d2d2d",
                                   fg="#00ff00", padx=8, pady=6)
        self.frame.pack(fill=tk.X, padx=8, pady=6)
        
        self.ml_enabled = tk.BooleanVar(value=True)
        self.sr_enabled = tk.BooleanVar(value=True)
        self.fibo_enabled = tk.BooleanVar(value=True)
        self.pa_enabled = tk.BooleanVar(value=True)
        self.candlestick_enabled = tk.BooleanVar(value=True)
        self.liquidity_enabled = tk.BooleanVar(value=True)
        self.mtf_enabled = tk.BooleanVar(value=True)
        
        self.setup_ui()
    
    def setup_ui(self):
        strategies_frame = tk.Frame(self.frame, bg="#2d2d2d")
        strategies_frame.pack(fill=tk.X, pady=4)
        
        # Grid de 3x3
        ml_check = tk.Checkbutton(strategies_frame, text="🤖 ML Models",
                                 variable=self.ml_enabled,
                                 font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                 selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                 activeforeground="#00ff00",
                                 command=self.on_config_change)
        ml_check.grid(row=0, column=0, sticky='w', padx=5, pady=2)
        
        sr_check = tk.Checkbutton(strategies_frame, text="📊 Support/Resist",
                                 variable=self.sr_enabled,
                                 font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                 selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                 activeforeground="#00ff00",
                                 command=self.on_config_change)
        sr_check.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        fibo_check = tk.Checkbutton(strategies_frame, text="🎯 Fibonacci",
                                    variable=self.fibo_enabled,
                                    font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                    selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                    activeforeground="#00ff00",
                                    command=self.on_config_change)
        fibo_check.grid(row=0, column=2, sticky='w', padx=5, pady=2)
        
        pa_check = tk.Checkbutton(strategies_frame, text="📈 Price Action",
                                  variable=self.pa_enabled,
                                  font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                  selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                  activeforeground="#00ff00",
                                  command=self.on_config_change)
        pa_check.grid(row=1, column=0, sticky='w', padx=5, pady=2)
        
        cs_check = tk.Checkbutton(strategies_frame, text="🕯️ Candlestick",
                                  variable=self.candlestick_enabled,
                                  font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                  selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                  activeforeground="#00ff00",
                                  command=self.on_config_change)
        cs_check.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        liq_check = tk.Checkbutton(strategies_frame, text="💧 Liquidity",
                                   variable=self.liquidity_enabled,
                                   font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                                   selectcolor="#1e1e1e", activebackground="#2d2d2d",
                                   activeforeground="#00ff00",
                                   command=self.on_config_change)
        liq_check.grid(row=1, column=2, sticky='w', padx=5, pady=2)
        
        mtf_check = tk.Checkbutton(strategies_frame, text="📊 Multi-TF (MTF)",
                           variable=self.mtf_enabled,
                           font=("Arial", 9), bg="#2d2d2d", fg="#ffffff",
                           selectcolor="#1e1e1e", activebackground="#2d2d2d",
                           activeforeground="#00ff00",
                           command=self.on_config_change)
        mtf_check.grid(row=2, column=0, sticky='w', padx=5, pady=2)
        
        # Señales
        stats_frame = tk.LabelFrame(self.frame, text="📡 Señales",
                                   font=("Arial", 9, "bold"), bg="#2d2d2d",
                                   fg="#ffffff", padx=6, pady=4)
        stats_frame.pack(fill=tk.X, pady=4)
        
        stats_row1 = tk.Frame(stats_frame, bg="#2d2d2d")
        stats_row1.pack(fill=tk.X, pady=1)
        
        tk.Label(stats_row1, text="Total:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=8, anchor='w').pack(side=tk.LEFT)
        self.total_signals_label = tk.Label(stats_row1, text="0",
                                           font=("Arial", 8, "bold"),
                                           bg="#2d2d2d", fg="#ffffff")
        self.total_signals_label.pack(side=tk.LEFT)
        
        tk.Label(stats_row1, text="Ejecutadas:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=10, anchor='w').pack(side=tk.LEFT, padx=10)
        self.executed_label = tk.Label(stats_row1, text="0",
                                      font=("Arial", 8, "bold"),
                                      bg="#2d2d2d", fg="#00ff00")
        self.executed_label.pack(side=tk.LEFT)
    
    def on_config_change(self):
        config = self.get_config()
        self.message_queue.put({'type': 'strategy_config', **config})
    
    def update_stats(self, total_signals, executed_signals):
        self.total_signals_label.config(text=str(total_signals))
        self.executed_label.config(text=str(executed_signals))
    
    def get_config(self):
        return {
            'ml_enabled': self.ml_enabled.get(),
            'sr_enabled': self.sr_enabled.get(),
            'fibo_enabled': self.fibo_enabled.get(),
            'pa_enabled': self.pa_enabled.get(),
            'candlestick_enabled': self.candlestick_enabled.get(),
            'liquidity_enabled': self.liquidity_enabled.get(),
            'mtf_enabled': self.mtf_enabled.get()
        }
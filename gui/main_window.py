"""
╔══════════════════════════════════════════════════════════════════════════╗
║               VENTANA PRINCIPAL GUI v5.2.7 + COOLDOWN                    ║
║                 + VISUALIZACIÓN GRÁFICA S/R                              ║
║                                                                          ║
║  🆕 v5.2.7: Columna de Cooldown en tabla de estadísticas                ║
║  🆕 NUEVO: Botón para ver estrategia gráficamente                       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import queue

from gui.mtf_panel import MTFDashboardPanel
from gui.strategies_panel import StrategiesControlPanel
from gui.autonomy_window import MLAutonomyWindow
from gui.charts_window import ChartsWindow
from gui.strategy_chart_window import StrategyChartWindow


class EnhancedTradingBotGUI:
    """GUI Principal del Bot v5.2.7 + Visualización Gráfica"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Bot XAUUSD ML v5.2")
        self.root.geometry("1700x950")
        self.root.configure(bg="#1e1e1e")
        
        self.message_queue = queue.Queue()
        
        # Variables de configuración
        self.max_daily_profit = tk.DoubleVar(value=1000.0)
        self.max_daily_loss = tk.DoubleVar(value=5000.0)
        self.lot_size = tk.DoubleVar(value=0.02)
        self.max_positions = tk.IntVar(value=10)
        self.daily_profit = tk.DoubleVar(value=0.0)
        
        self.current_price = 0.0
        
        # Datos de estadísticas por estrategia (AHORA CON COOLDOWN)
        self.strategy_stats = {
            'ML MODELS': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0},
            'PRICE ACTION': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0},
            'S/R': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0},
            'CANDLESTICK': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0},
            'FIBONACCI': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0},
            'LIQUIDEZ': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0, 'cooldown_remaining': 0}
        }
        
        # Referencias a ventanas adicionales
        self.autonomy_window = None
        self.charts_window = None
        self.strategy_chart_window = None
        
        self.setup_ui()
        self.update_gui()
    
    def setup_ui(self):
        # HEADER
        header_frame = tk.Frame(self.root, bg="#2d2d2d", height=70)
        header_frame.pack(fill=tk.X, padx=10, pady=8)
        header_frame.pack_propagate(False)
        
        title = tk.Label(header_frame, text="🤖 BOT XAUUSD ML v5.2",
                font=("Arial", 16, "bold"), bg="#2d2d2d", fg="#00ff00")
        title.pack(side=tk.TOP, pady=3)
        
        self.status_label = tk.Label(header_frame, text="🔴 Desconectado",
                                     font=("Arial", 10), bg="#2d2d2d", fg="#ff4444")
        self.status_label.pack(side=tk.TOP)
        
        # CONTENEDOR PRINCIPAL
        main_container = tk.Frame(self.root, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # PANEL IZQUIERDO
        left_panel = tk.Frame(main_container, bg="#2d2d2d", width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        left_panel.pack_propagate(False)
        
        # PANEL DERECHO
        right_panel = tk.Frame(main_container, bg="#2d2d2d")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # === LEFT PANEL ===
        self.setup_left_panel(left_panel)
        
        # === RIGHT PANEL ===
        self.setup_right_panel(right_panel)
    
    def setup_left_panel(self, left_panel):
        """Configura panel izquierdo"""
        
        # Configuración
        config_frame = tk.LabelFrame(left_panel, text="⚙️ CONFIGURACIÓN",
                                    font=("Arial", 9, "bold"), bg="#2d2d2d",
                                    fg="#ffffff", padx=8, pady=6)
        config_frame.pack(fill=tk.X, padx=8, pady=6)
        
        profit_frame = tk.Frame(config_frame, bg="#2d2d2d")
        profit_frame.pack(fill=tk.X, pady=3)
        tk.Label(profit_frame, text="💰 Ganancia Máx:", font=("Arial", 8),
                bg="#2d2d2d", fg="#ffffff", width=14, anchor='w').pack(side=tk.LEFT)
        profit_spin = tk.Spinbox(profit_frame, from_=10, to=10000, increment=10,
                                textvariable=self.max_daily_profit, width=7,
                                font=("Arial", 8, "bold"), bg="#1e1e1e", fg="#44ff44")
        profit_spin.pack(side=tk.RIGHT)
        
        loss_frame = tk.Frame(config_frame, bg="#2d2d2d")
        loss_frame.pack(fill=tk.X, pady=3)
        tk.Label(loss_frame, text="🛡️ Pérdida Máx:", font=("Arial", 8),
                bg="#2d2d2d", fg="#ffffff", width=14, anchor='w').pack(side=tk.LEFT)
        loss_spin = tk.Spinbox(loss_frame, from_=10, to=5000, increment=50,
                              textvariable=self.max_daily_loss, width=7,
                              font=("Arial", 8, "bold"), bg="#1e1e1e", fg="#ff4444")
        loss_spin.pack(side=tk.RIGHT)
        
        lot_frame = tk.Frame(config_frame, bg="#2d2d2d")
        lot_frame.pack(fill=tk.X, pady=3)
        tk.Label(lot_frame, text="📊 Lote:", font=("Arial", 8),
                bg="#2d2d2d", fg="#ffffff", width=14, anchor='w').pack(side=tk.LEFT)
        lot_spin = tk.Spinbox(lot_frame, from_=0.01, to=10.0, increment=0.01,
                             textvariable=self.lot_size, width=7, format="%.2f",
                             font=("Arial", 8, "bold"), bg="#1e1e1e", fg="#ffaa00")
        lot_spin.pack(side=tk.RIGHT)
        
        max_ops_frame = tk.Frame(config_frame, bg="#2d2d2d")
        max_ops_frame.pack(fill=tk.X, pady=3)
        tk.Label(max_ops_frame, text="🎯 Max Ops:", font=("Arial", 8),
                bg="#2d2d2d", fg="#ffffff", width=14, anchor='w').pack(side=tk.LEFT)
        max_ops_spin = tk.Spinbox(max_ops_frame, from_=1, to=20, increment=1,
                                  textvariable=self.max_positions, width=7,
                                  font=("Arial", 8, "bold"), bg="#1e1e1e", fg="#00aaff")
        max_ops_spin.pack(side=tk.RIGHT)
        
        btn_frame = tk.Frame(config_frame, bg="#2d2d2d")
        btn_frame.pack(fill=tk.X, pady=4)
        
        apply_btn = tk.Button(btn_frame, text="✅ Aplicar",
                             font=("Arial", 8, "bold"), bg="#44ff44", fg="#000000",
                             command=self.apply_config, cursor="hand2", width=13)
        apply_btn.pack(side=tk.LEFT, padx=2)
        
        reset_btn = tk.Button(btn_frame, text="🔄 Reset",
                             font=("Arial", 8, "bold"), bg="#ffaa00", fg="#000000",
                             command=self.reset_trading, cursor="hand2", width=13)
        reset_btn.pack(side=tk.RIGHT, padx=2)
        
        # Balance Diario
        daily_frame = tk.LabelFrame(left_panel, text="💰 TOTAL PROFIT",
                                   font=("Arial", 10, "bold"), bg="#2d2d2d",
                                   fg="#ffffff", padx=8, pady=5)
        daily_frame.pack(fill=tk.X, padx=8, pady=6)
        
        self.daily_balance_label = tk.Label(daily_frame, text="$0.00",
                                           font=("Arial", 20, "bold"), bg="#2d2d2d", fg="#44ff44")
        self.daily_balance_label.pack()
        
        # Panel de Estrategias
        self.strategies_panel = StrategiesControlPanel(left_panel, self.message_queue)
        
        # Panel MTF
        self.mtf_dashboard = MTFDashboardPanel(left_panel, self.message_queue)
        
        # BOTONES DE VENTANAS ADICIONALES
        windows_btn_frame = tk.Frame(left_panel, bg="#2d2d2d")
        windows_btn_frame.pack(fill=tk.X, padx=8, pady=8)
        
        # Botón Autonomía
        autonomy_btn = tk.Button(windows_btn_frame,
                                text="🤖 PANEL DE AUTONOMÍA ML",
                                font=("Arial", 9, "bold"), bg="#00aaff", fg="#ffffff",
                                command=self.open_autonomy_window, cursor="hand2")
        autonomy_btn.pack(fill=tk.X, pady=2)
        
        # Botón Gráficas
        charts_btn = tk.Button(windows_btn_frame,
                              text="📊 GRÁFICAS DE PROFIT",
                              font=("Arial", 9, "bold"), bg="#00ff88", fg="#000000",
                              command=self.open_charts_window, cursor="hand2")
        charts_btn.pack(fill=tk.X, pady=2)
        
        # 🆕 NUEVO: Botón Visualización Gráfica S/R
        strategy_chart_btn = tk.Button(windows_btn_frame,
                                      text="📈 VER ESTRATEGIA GRÁFICAMENTE",
                                      font=("Arial", 9, "bold"), bg="#FFD700", fg="#000000",
                                      command=self.open_strategy_chart_window, cursor="hand2")
        strategy_chart_btn.pack(fill=tk.X, pady=2)

    def setup_right_panel(self, right_panel):
        """Configura panel derecho con tabla de operaciones, estadísticas y log"""
        
        # === TABLA DE OPERACIONES (MÁS GRANDE) ===
        positions_frame = tk.LabelFrame(right_panel, text="📋 OPERACIONES",
                                       font=("Arial", 10, "bold"), bg="#2d2d2d",
                                       fg="#ffffff", padx=10, pady=8)
        positions_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        pos_container = tk.Frame(positions_frame, bg="#2d2d2d")
        pos_container.pack(fill=tk.BOTH, expand=True)
        
        style = ttk.Style()
        style.configure("Treeview", background="#1e1e1e", foreground="white",
                       fieldbackground="#1e1e1e", font=("Consolas", 8))
        style.configure("Treeview.Heading", font=("Arial", 9, "bold"))
        
        self.positions_tree = ttk.Treeview(pos_container,
                                  columns=("Estado", "Estrategia", "Tipo", "P.Entrada",
                                          "SL", "TP", "P.Actual", "Lotes", "Ganancia",
                                          "Trailing", "Breakeven", "MTF", "Hora"),
                                  show="headings", height=12)
        
        self.positions_tree.heading("Estado", text="Estado")
        self.positions_tree.heading("Estrategia", text="Estrategia")
        self.positions_tree.heading("Tipo", text="Tipo")
        self.positions_tree.heading("P.Entrada", text="P.Entrada")
        self.positions_tree.heading("SL", text="SL")
        self.positions_tree.heading("TP", text="TP")
        self.positions_tree.heading("P.Actual", text="P.Actual")
        self.positions_tree.heading("Lotes", text="Lotes")
        self.positions_tree.heading("Ganancia", text="Ganancia")
        self.positions_tree.heading("Trailing", text="Trail")
        self.positions_tree.heading("Breakeven", text="BE")
        self.positions_tree.heading("MTF", text="MTF")
        self.positions_tree.heading("Hora", text="Hora")
        
        self.positions_tree.column("Estado", width=70, anchor='center')
        self.positions_tree.column("Estrategia", width=75, anchor='center')
        self.positions_tree.column("Tipo", width=55, anchor='center')
        self.positions_tree.column("P.Entrada", width=70, anchor='center')
        self.positions_tree.column("SL", width=70, anchor='center')
        self.positions_tree.column("TP", width=70, anchor='center')
        self.positions_tree.column("P.Actual", width=70, anchor='center')
        self.positions_tree.column("Lotes", width=50, anchor='center')
        self.positions_tree.column("Ganancia", width=70, anchor='center')
        self.positions_tree.column("Trailing", width=35, anchor='center')
        self.positions_tree.column("Breakeven", width=35, anchor='center')
        self.positions_tree.column("MTF", width=35, anchor='center')
        self.positions_tree.column("Hora", width=60, anchor='center')
        
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        pos_scrollbar = ttk.Scrollbar(pos_container, orient="vertical",
                                     command=self.positions_tree.yview)
        pos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.configure(yscrollcommand=pos_scrollbar.set)
        
        # TABLA DE ESTADÍSTICAS POR ESTRATEGIA (CON COOLDOWN)
        stats_frame = tk.LabelFrame(right_panel, text="📊 ESTADÍSTICAS POR ESTRATEGIA",
                                   font=("Arial", 10, "bold"), bg="#2d2d2d",
                                   fg="#ffffff", padx=10, pady=8)
        stats_frame.pack(fill=tk.X, padx=8, pady=8)
        
        stats_container = tk.Frame(stats_frame, bg="#2d2d2d")
        stats_container.pack(fill=tk.BOTH, expand=True)
        
        # Estilo para tabla de estadísticas
        style.configure("Stats.Treeview", background="#1e1e1e", foreground="white",
                       fieldbackground="#1e1e1e", font=("Consolas", 9), rowheight=25)
        style.configure("Stats.Treeview.Heading", font=("Arial", 9, "bold"))
        
        self.stats_tree = ttk.Treeview(stats_container,
                                      columns=("Estrategia", "N° Operaciones", "Ganadas", 
                                              "Perdidas", "Profit Total", "Cooldown"),
                                      show="headings", height=6, style="Stats.Treeview")
        
        self.stats_tree.heading("Estrategia", text="ESTRATEGIA")
        self.stats_tree.heading("N° Operaciones", text="N° OPS")
        self.stats_tree.heading("Ganadas", text="GANADAS")
        self.stats_tree.heading("Perdidas", text="PERDIDAS")
        self.stats_tree.heading("Profit Total", text="PROFIT")
        self.stats_tree.heading("Cooldown", text="COOLDOWN")
        
        self.stats_tree.column("Estrategia", width=130, anchor='w')
        self.stats_tree.column("N° Operaciones", width=90, anchor='center')
        self.stats_tree.column("Ganadas", width=90, anchor='center')
        self.stats_tree.column("Perdidas", width=90, anchor='center')
        self.stats_tree.column("Profit Total", width=120, anchor='center')
        self.stats_tree.column("Cooldown", width=120, anchor='center')
        
        self.stats_tree.pack(fill=tk.BOTH, expand=True)
        
        # BOTÓN RESET STATS
        stats_button_frame = tk.Frame(stats_frame, bg="#2d2d2d")
        stats_button_frame.pack(fill=tk.X, padx=8, pady=5)
        
        reset_stats_btn = tk.Button(stats_button_frame,
                                    text="🔄 Reset Stats",
                                    font=("Arial", 9, "bold"),
                                    bg="#ff4444",
                                    fg="#ffffff",
                                    command=self.reset_strategy_stats,
                                    cursor="hand2",
                                    width=15)
        reset_stats_btn.pack(side=tk.RIGHT, padx=5)
        
        stats_info_label = tk.Label(stats_button_frame,
                                    text="Resetea todas las estadísticas a cero",
                                    font=("Arial", 8),
                                    bg="#2d2d2d",
                                    fg="#aaaaaa")
        stats_info_label.pack(side=tk.LEFT, padx=5)
        
        # ✅ INICIALIZAR TABLA CON DATOS VACÍOS
        self.update_strategy_stats_table()
        
        # Log (MÁS GRANDE)
        log_frame = tk.LabelFrame(right_panel, text="📋 LOG",
                                 font=("Arial", 9, "bold"), bg="#2d2d2d",
                                 fg="#ffffff", padx=8, pady=6)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, bg="#1e1e1e",
                                                  fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def open_charts_window(self):
        """Abre ventana de gráficas de profit"""
        if self.charts_window is None or not tk.Toplevel.winfo_exists(self.charts_window.window):
            self.charts_window = ChartsWindow(self.root, self.message_queue)
        else:
            self.charts_window.window.lift()
    
    def open_autonomy_window(self):
        """Abre ventana de Autonomía ML"""
        if self.autonomy_window is None or not tk.Toplevel.winfo_exists(self.autonomy_window.window):
            self.autonomy_window = MLAutonomyWindow(self.root, self.message_queue)
        else:
            self.autonomy_window.window.lift()
    
    def open_strategy_chart_window(self):
        """🆕 Abre ventana de visualización gráfica de estrategia S/R"""
        if self.strategy_chart_window is None or not tk.Toplevel.winfo_exists(self.strategy_chart_window.window):
            self.strategy_chart_window = StrategyChartWindow(self.root)
        else:
            self.strategy_chart_window.window.lift()
    
    def update_strategy_stats_table(self):
        """Actualiza la tabla de estadísticas CON COOLDOWN"""
        # Limpiar tabla
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Orden de visualización
        order = ['ML MODELS', 'PRICE ACTION', 'S/R', 'CANDLESTICK', 'FIBONACCI', 'LIQUIDEZ']
        
        # Encontrar mejor estrategia (mayor profit)
        best_strategy = None
        max_profit = float('-inf')
        for strategy_name, stats in self.strategy_stats.items():
            if stats['profit'] > max_profit:
                max_profit = stats['profit']
                best_strategy = strategy_name
        
        # Insertar datos en el orden especificado
        for strategy_name in order:
            stats = self.strategy_stats[strategy_name]
            
            # Formatear profit con color
            profit = stats['profit']
            if profit > 0:
                profit_text = f"💚 ${profit:.2f}"
                tag = 'profit_positive'
            elif profit < 0:
                profit_text = f"❤️ ${profit:.2f}"
                tag = 'profit_negative'
            else:
                profit_text = "$0.00"
                tag = 'profit_neutral'
            
            # FORMATEAR COOLDOWN
            cooldown_remaining = stats.get('cooldown_remaining', 0)
            
            if cooldown_remaining > 0:
                if cooldown_remaining >= 60:
                    cooldown_text = f"⏱️ {cooldown_remaining/60:.0f}h {cooldown_remaining%60:.0f}m"
                else:
                    cooldown_text = f"⏱️ {cooldown_remaining:.0f}m"
                cooldown_tag = 'cooldown_active'
            else:
                cooldown_text = "✅ OK"
                cooldown_tag = 'cooldown_ready'
            
            # Marcar mejor estrategia
            if strategy_name == best_strategy and profit > 0:
                tag = 'best_strategy'
                strategy_display = f"🏆 {strategy_name}"
            else:
                strategy_display = strategy_name
            
            # Determinar tag final (cooldown tiene prioridad visual)
            if cooldown_remaining > 0:
                final_tag = cooldown_tag
            else:
                final_tag = tag
            
            self.stats_tree.insert("", "end", values=(
                strategy_display,
                stats['operations'],
                stats['wins'],
                stats['losses'],
                profit_text,
                cooldown_text
            ), tags=(final_tag,))
        
        # Configurar colores
        self.stats_tree.tag_configure('profit_positive', background='#1a4a1a')
        self.stats_tree.tag_configure('profit_negative', background='#4a1a1a')
        self.stats_tree.tag_configure('profit_neutral', background='#2d2d2d')
        self.stats_tree.tag_configure('best_strategy', background='#2a5a2a', foreground='#FFD700')
        
        # Colores para cooldown
        self.stats_tree.tag_configure('cooldown_active', background='#4a2a1a', foreground='#ff8844')
        self.stats_tree.tag_configure('cooldown_ready', background='#1a4a2a', foreground='#44ff88')

    def apply_config(self):
        """Aplica configuración"""
        self.message_queue.put({
            'type': 'config',
            'max_profit': self.max_daily_profit.get(),
            'max_loss': self.max_daily_loss.get(),
            'lot_size': self.lot_size.get(),
            'max_positions': self.max_positions.get()
        })
        
        self.log_message(f"✅ Config: +${self.max_daily_profit.get():.0f}/-${self.max_daily_loss.get():.0f}/Lote:{self.lot_size.get():.2f}/Max:{self.max_positions.get()}")
    
    def reset_trading(self):
        """Resetea trading"""
        self.message_queue.put({'type': 'reset_trading'})
        self.log_message("🔄 Reseteo de trading solicitado")
    
    def reset_strategy_stats(self):
        """Resetea estadísticas de estrategias"""
        response = messagebox.askyesno(
            "Confirmar Reset",
            "¿Resetear las estadísticas de todas las estrategias?\n\nSe perderán todos los datos de:\n• Operaciones\n• Ganancias/Pérdidas\n• Profit acumulado"
        )
        if response:
            self.message_queue.put({'type': 'reset_strategy_stats'})
            self.log_message("📊 Reseteo de estadísticas solicitado")
            messagebox.showinfo("Reset Completado", "Las estadísticas han sido reseteadas a cero.")
    
    def update_daily_balance(self, balance):
        """Actualiza total profit"""
        self.daily_profit.set(balance)
        
        if balance > 0:
            self.daily_balance_label.config(text=f"+${balance:.2f}", fg="#44ff44")
        elif balance < 0:
            self.daily_balance_label.config(text=f"${balance:.2f}", fg="#ff4444")
        else:
            self.daily_balance_label.config(text="$0.00", fg="#ffffff")
    
    def update_status(self, connected):
        """Actualiza estado de conexión"""
        if connected:
            self.status_label.config(text="🟢 Conectado", fg="#44ff44")
        else:
            self.status_label.config(text="🔴 Desconectado", fg="#ff4444")
    
    def update_positions(self, positions):
        """Actualiza tabla de posiciones"""
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        for pos in positions:
            estado = pos.get('estado', 'ABIERTA')
            estrategia = pos.get('estrategia', 'N/A')
            tipo = pos['tipo']
            ganancia = pos['ganancia']
            
            ganancia_text = f"💚 ${ganancia:.2f}" if ganancia > 0 else f"❤️ ${ganancia:.2f}"
            
            trailing = "✅" if pos.get('trailing_active') else "⚪"
            breakeven = "✅" if pos.get('breakeven_active') else "⚪"
            
            mtf_status = pos.get('mtf_status', '')
            mtf_icon = {"approved": "✅", "blocked": "⛔", "unknown": "—"}.get(mtf_status, "—")
            
            if estado == "🟢 ABIERTA":
                tag = 'open_profit' if ganancia > 0 else 'open_loss'
            else:
                tag = 'closed_profit' if ganancia > 0 else 'closed_loss'
            
            self.positions_tree.insert("", "end", values=(
                estado,
                estrategia,
                tipo,
                f"${pos.get('precio_entrada', 0):.2f}",
                f"${pos.get('sl', 0):.2f}",
                f"${pos.get('tp', 0):.2f}",
                f"${pos.get('precio_actual', 0):.2f}",
                pos.get('volumen', 0),
                ganancia_text,
                trailing,
                breakeven,
                mtf_icon,
                pos.get('hora', '—')
            ), tags=(tag,))
        
        self.positions_tree.tag_configure('open_profit', background='#1a4a1a')
        self.positions_tree.tag_configure('open_loss', background='#4a1a1a')
        self.positions_tree.tag_configure('closed_profit', background='#0d2d0d')
        self.positions_tree.tag_configure('closed_loss', background='#2d0d0d')
    
    def log_message(self, message):
        """Agrega mensaje al log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        lines = self.log_text.get("1.0", tk.END).split("\n")
        if len(lines) > 50:
            self.log_text.delete("1.0", "2.0")
    
    def update_profit_charts(self, hourly_data, daily_data):
        """Actualiza datos de gráficas en la ventana de gráficas"""
        if self.charts_window and tk.Toplevel.winfo_exists(self.charts_window.window):
            self.charts_window.update_charts(hourly_data, daily_data)
    
    def update_strategy_stats(self, stats_data):
        """Actualiza estadísticas por estrategia CON COOLDOWN"""
        # Mapeo de nombres internos a nombres mostrados
        strategy_mapping = {
            'ml': 'ML MODELS',
            'price_action': 'PRICE ACTION',
            'sr': 'S/R',
            'candlestick': 'CANDLESTICK',
            'fibo': 'FIBONACCI',
            'liquidity': 'LIQUIDEZ'
        }
        
        # Actualizar datos (incluyendo cooldown)
        for internal_name, display_name in strategy_mapping.items():
            if internal_name in stats_data:
                stat = stats_data[internal_name]
                
                # Actualizar todas las stats incluyendo cooldown
                self.strategy_stats[display_name] = {
                    'operations': stat.get('operations', 0),
                    'wins': stat.get('wins', 0),
                    'losses': stat.get('losses', 0),
                    'profit': stat.get('profit', 0.0),
                    'cooldown_remaining': stat.get('cooldown_remaining', 0)
                }
        
        # Actualizar tabla
        self.update_strategy_stats_table()
    
    def update_gui(self):
        """Loop principal de actualización GUI"""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                msg_type = msg.get('type')
                
                if msg_type == 'status':
                    self.update_status(msg['connected'])
                elif msg_type == 'positions':
                    self.update_positions(msg['positions'])
                elif msg_type == 'log':
                    self.log_message(msg['message'])
                elif msg_type == 'daily_balance':
                    self.update_daily_balance(msg['balance'])
                elif msg_type == 'mtf_analysis':
                    if hasattr(self, 'mtf_dashboard'):
                        self.mtf_dashboard.update_mtf_data(msg['analysis'])
                elif msg_type == 'ml_status':
                    if self.autonomy_window and tk.Toplevel.winfo_exists(self.autonomy_window.window):
                        self.autonomy_window.update_ml_status(msg['data'])
                elif msg_type == 'profit_charts':
                    self.update_profit_charts(msg['hourly'], msg['daily'])
                elif msg_type == 'signal_stats':
                    self.strategies_panel.update_stats(msg['total'], msg['executed'])
                elif msg_type == 'autonomy_data':
                    if self.autonomy_window and tk.Toplevel.winfo_exists(self.autonomy_window.window):
                        self.autonomy_window.update_all_data(msg['data'])
                elif msg_type == 'strategy_stats':
                    self.update_strategy_stats(msg['stats'])
                        
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_gui)
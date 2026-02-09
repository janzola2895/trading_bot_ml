"""
╔══════════════════════════════════════════════════════════════════════════╗
║           VISUALIZACIÓN GRÁFICA DE ESTRATEGIA S/R v2.0 MEJORADO          ║
║                                                                          ║
║  🎨 DISEÑO PROFESIONAL:                                                  ║
║  ✅ Velas japonesas grandes y claras (estilo TradingView)               ║
║  ✅ Niveles S/R con etiquetas BUY/SELL visibles                         ║
║  ✅ Líneas de tendencia EMA con colores distintivos                     ║
║  ✅ Señales marcadas con flechas y texto explicativo                    ║
║  ✅ Fondo oscuro profesional (#0e0e0e)                                  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class StrategyChartWindow:
    """
    Ventana de visualización gráfica de la estrategia Support/Resistance
    
    🎨 MEJORAS v2.0:
    - Velas japonesas más grandes y visibles
    - Niveles S/R con etiquetas "🔴 SELL" y "🟢 BUY"
    - Líneas EMA destacadas
    - Señales actuales claramente marcadas
    - Grid profesional sutil
    """
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Estrategia Support/Resistance - Visualización Gráfica v2.0")
        self.window.geometry("1600x900")
        self.window.configure(bg="#1e1e1e")
        
        # Sistema S/R
        from strategies.support_resistance import SupportResistanceSystem
        self.sr_system = SupportResistanceSystem()
        
        # Variables de datos
        self.df = None
        self.current_price = 0
        self.levels = []
        self.current_signal = None
        
        self.setup_ui()
        self.update_chart()
    
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # HEADER
        header = tk.Frame(self.window, bg="#2d2d2d", height=70)
        header.pack(fill=tk.X, padx=10, pady=8)
        header.pack_propagate(False)
        
        title = tk.Label(header, text="📊 VISUALIZACIÓN ESTRATEGIA S/R",
                        font=("Arial", 16, "bold"), bg="#2d2d2d", fg="#00ff00")
        title.pack(pady=5)
        
        subtitle = tk.Label(header, text="Niveles de Soporte y Resistencia en tiempo real",
                           font=("Arial", 10), bg="#2d2d2d", fg="#aaaaaa")
        subtitle.pack()
        
        # CONTENEDOR PRINCIPAL
        main_container = tk.Frame(self.window, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # PANEL IZQUIERDO - GRÁFICO (80%)
        chart_panel = tk.Frame(main_container, bg="#0e0e0e")
        chart_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.chart_frame = tk.Frame(chart_panel, bg="#0e0e0e")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.setup_chart()
        
        # PANEL DERECHO - INFORMACIÓN (20%)
        info_panel = tk.Frame(main_container, bg="#2d2d2d", width=320)
        info_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        info_panel.pack_propagate(False)
        
        # Estado actual
        status_frame = tk.LabelFrame(info_panel, text="📊 ESTADO ACTUAL",
                                     font=("Arial", 10, "bold"), bg="#2d2d2d",
                                     fg="#00ff00", padx=10, pady=8)
        status_frame.pack(fill=tk.X, padx=8, pady=8)
        
        self.price_label = tk.Label(status_frame, text="Precio: $0.00",
                                    font=("Arial", 12, "bold"), bg="#2d2d2d", fg="#FFD700")
        self.price_label.pack(pady=3)
        
        self.signal_label = tk.Label(status_frame, text="Señal: Esperando...",
                                     font=("Arial", 10), bg="#2d2d2d", fg="#ffffff")
        self.signal_label.pack(pady=3)
        
        self.confidence_label = tk.Label(status_frame, text="Confianza: 0%",
                                        font=("Arial", 9), bg="#2d2d2d", fg="#aaaaaa")
        self.confidence_label.pack(pady=3)
        
        # Niveles detectados
        levels_frame = tk.LabelFrame(info_panel, text="🎯 NIVELES S/R",
                                    font=("Arial", 10, "bold"), bg="#2d2d2d",
                                    fg="#00ff00", padx=10, pady=8)
        levels_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Tabla de niveles
        self.levels_tree = ttk.Treeview(levels_frame,
                                       columns=("Tipo", "Precio", "Toques"),
                                       show="headings", height=12)
        
        self.levels_tree.heading("Tipo", text="Tipo")
        self.levels_tree.heading("Precio", text="Precio")
        self.levels_tree.heading("Toques", text="Fuerza")
        
        self.levels_tree.column("Tipo", width=80, anchor='center')
        self.levels_tree.column("Precio", width=100, anchor='center')
        self.levels_tree.column("Toques", width=60, anchor='center')
        
        self.levels_tree.pack(fill=tk.BOTH, expand=True)
        
        # Controles
        controls_frame = tk.Frame(info_panel, bg="#2d2d2d", height=60)
        controls_frame.pack(fill=tk.X, padx=8, pady=8)
        controls_frame.pack_propagate(False)
        
        refresh_btn = tk.Button(controls_frame, text="🔄 Actualizar",
                               font=("Arial", 9, "bold"), bg="#44ff44", fg="#000000",
                               command=self.update_chart, cursor="hand2")
        refresh_btn.pack(pady=3, fill=tk.X)
        
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(controls_frame, text="Auto-actualizar (5s)",
                                   variable=self.auto_update_var,
                                   font=("Arial", 8), bg="#2d2d2d", fg="#ffffff",
                                   selectcolor="#1e1e1e")
        auto_check.pack(pady=3)
        
        # Auto-actualización
        self.auto_update_loop()
    
    def setup_chart(self):
        """Configura el área de gráfica - ESTILO PROFESIONAL MEJORADO v2.0"""
        # Crear figura con fondo oscuro profesional
        self.fig = Figure(figsize=(14, 9), dpi=100, facecolor='#0e0e0e')
        self.ax = self.fig.add_subplot(111, facecolor='#1a1a1a')
        
        # Grid profesional sutil
        self.ax.grid(True, alpha=0.12, color='#505050', linestyle='-', linewidth=0.8, which='major')
        self.ax.grid(True, alpha=0.05, color='#404040', linestyle='-', linewidth=0.4, which='minor')
        self.ax.minorticks_on()
        
        # Etiquetas con mejor contraste
        self.ax.set_xlabel('Tiempo (Barras) →', color='#e0e0e0', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Precio XAUUSD (USD)', color='#e0e0e0', fontsize=12, fontweight='bold')
        self.ax.tick_params(colors='#c0c0c0', labelsize=10, width=1.8, length=7)
        
        # Bordes del gráfico más visibles
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#505050')
            spine.set_linewidth(2)
        
        # Ajustar márgenes
        self.fig.subplots_adjust(left=0.07, right=0.97, top=0.96, bottom=0.08)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def get_market_data(self):
        """Obtiene datos del mercado desde MT5"""
        try:
            # Obtener 200 barras para análisis
            rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M30, 0, 200)
            
            if rates is None or len(rates) == 0:
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calcular indicadores
            import ta
            df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
            df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['ema_100'] = ta.trend.ema_indicator(df['close'], window=100)
            
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error obteniendo datos: {e}")
            return None
    
    def draw_candlesticks(self, df_plot):
        """
        Dibuja velas japonesas MEJORADAS - más grandes y visibles
        Estilo TradingView profesional
        """
        for i in range(len(df_plot)):
            row = df_plot.iloc[i]
            
            # Colores intensos y profesionales
            if row['close'] >= row['open']:
                # Vela alcista (verde brillante)
                body_color = '#00ff88'
                wick_color = '#00ff88'
            else:
                # Vela bajista (rojo intenso)
                body_color = '#ff4444'
                wick_color = '#ff4444'
            
            # Dibujar mecha (wick) - más gruesa
            self.ax.plot([i, i], [row['low'], row['high']], 
                        color=wick_color, linewidth=1.8, alpha=0.9, zorder=1)
            
            # Dibujar cuerpo (body) - MÁS ANCHO para mejor visibilidad
            body_height = abs(row['close'] - row['open'])
            body_bottom = min(row['open'], row['close'])
            
            # Ancho de vela aumentado: 0.7 (antes era 0.6)
            rect = Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                           facecolor=body_color, edgecolor=body_color,
                           linewidth=1.5, alpha=0.95, zorder=2)
            self.ax.add_patch(rect)
    
    def draw_ema_lines(self, df_plot):
        """
        Dibuja líneas EMA mejoradas - más visibles y profesionales
        """
        indices = range(len(df_plot))
        
        # EMA 21 - Azul brillante (línea más gruesa)
        self.ax.plot(indices, df_plot['ema_21'], 
                    color='#00aaff', linewidth=2.5, alpha=0.95, 
                    label='EMA 21', zorder=3, linestyle='-')
        
        # EMA 50 - Naranja intenso
        self.ax.plot(indices, df_plot['ema_50'], 
                    color='#ff8800', linewidth=2.2, alpha=0.90, 
                    label='EMA 50', zorder=3, linestyle='-')
        
        # EMA 100 - Magenta
        self.ax.plot(indices, df_plot['ema_100'], 
                    color='#ff00ff', linewidth=2.0, alpha=0.85, 
                    label='EMA 100', zorder=3, linestyle='--')
        
        # Leyenda mejorada
        legend = self.ax.legend(loc='upper left', fontsize=10, 
                               facecolor='#2d2d2d', edgecolor='#505050',
                               framealpha=0.95, labelcolor='#e0e0e0')
        legend.get_frame().set_linewidth(1.5)
    
    def draw_sr_levels(self, levels, df_plot, current_price):
        """
        Dibuja niveles S/R MEJORADOS con etiquetas BUY/SELL grandes y claras
        """
        y_min = df_plot['low'].min()
        y_max = df_plot['high'].max()
        price_range = y_max - y_min
        
        for level_data in levels[:8]:  # Top 8 niveles
            level_price = level_data['level']
            level_type = level_data['type']
            touches = level_data.get('total_touches', level_data.get('touches', 1))
            
            # Colores según tipo
            if level_type == 'resistance':
                line_color = '#ff3366'  # Rojo más intenso
                zone_color = '#ff3366'
                label_text = " SELL"
                label_color = '#ff3366'
            else:  # support
                line_color = '#00ff66'  # Verde más intenso
                zone_color = '#00ff66'
                label_text = " BUY"
                label_color = '#00ff66'
            
            # Grosor de línea según fuerza
            if touches >= 4:
                linewidth = 2.8
                alpha_line = 0.95
                alpha_zone = 0.15
            elif touches >= 3:
                linewidth = 2.3
                alpha_line = 0.85
                alpha_zone = 0.12
            else:
                linewidth = 1.8
                alpha_line = 0.75
                alpha_zone = 0.08
            
            # Dibujar línea principal del nivel
            self.ax.axhline(y=level_price, color=line_color, 
                          linestyle='--', linewidth=linewidth, 
                          alpha=alpha_line, zorder=4)
            
            # Zona de influencia (±8 USD)
            zone_height = 8
            zone_rect = Rectangle((0, level_price - zone_height/2), 
                                 len(df_plot), zone_height,
                                 facecolor=zone_color, alpha=alpha_zone, 
                                 zorder=0)
            self.ax.add_patch(zone_rect)
            
            # ETIQUETA GRANDE Y CLARA con BUY/SELL
            # Posición en el lado derecho del gráfico
            label_x = len(df_plot) - 2
            
            # Fondo para la etiqueta (caja)
            bbox_props = dict(boxstyle='round,pad=0.6', 
                            facecolor='#0e0e0e', 
                            edgecolor=label_color, 
                            linewidth=2.5, 
                            alpha=0.95)
            
            # Texto con precio y señal
            label_full = f"{label_text}\n${level_price:.2f}"
            
            self.ax.text(label_x, level_price, label_full,
                        fontsize=11, fontweight='bold',
                        color=label_color,
                        bbox=bbox_props,
                        ha='right', va='center',
                        zorder=10)
    
    def draw_current_signal(self, signal_data, df_plot):
        """
        Dibuja la señal actual con flecha y texto explicativo GRANDE
        """
        if not signal_data:
            return
        
        signal_type = signal_data['signal']
        confidence = signal_data['confidence']
        level_value = signal_data.get('level_value', 0)
        
        # Encontrar posición de la señal (última barra)
        signal_x = len(df_plot) - 1
        signal_y = df_plot.iloc[-1]['close']
        
        if signal_type == 1:  # BUY
            # Flecha verde hacia arriba (MÁS GRANDE)
            arrow_props = dict(arrowstyle='->', lw=4, color='#00ff66')
            self.ax.annotate('', xy=(signal_x, signal_y + 15), 
                           xytext=(signal_x, signal_y - 10),
                           arrowprops=arrow_props, zorder=15)
            
            # Texto explicativo grande
            bbox_props = dict(boxstyle='round,pad=0.8', 
                            facecolor='#00ff66', 
                            edgecolor='#00ff66',
                            linewidth=2,
                            alpha=0.95)
            
            text = f" BUY SIGNAL\n{confidence*100:.0f}% conf\n${level_value:.2f}"
            
            self.ax.text(signal_x - 5, signal_y + 25, text,
                        fontsize=12, fontweight='bold',
                        color='#000000',
                        bbox=bbox_props,
                        ha='center', va='bottom',
                        zorder=15)
        
        else:  # SELL
            # Flecha roja hacia abajo (MÁS GRANDE)
            arrow_props = dict(arrowstyle='->', lw=4, color='#ff3366')
            self.ax.annotate('', xy=(signal_x, signal_y - 15), 
                           xytext=(signal_x, signal_y + 10),
                           arrowprops=arrow_props, zorder=15)
            
            # Texto explicativo grande
            bbox_props = dict(boxstyle='round,pad=0.8', 
                            facecolor='#ff3366', 
                            edgecolor='#ff3366',
                            linewidth=2,
                            alpha=0.95)
            
            text = f" SELL SIGNAL\n{confidence*100:.0f}% conf\n${level_value:.2f}"
            
            self.ax.text(signal_x - 5, signal_y - 25, text,
                        fontsize=12, fontweight='bold',
                        color='#ffffff',
                        bbox=bbox_props,
                        ha='center', va='top',
                        zorder=15)
    
    def update_chart(self):
        """Actualiza el gráfico completo"""
        # Obtener datos
        self.df = self.get_market_data()
        
        if self.df is None or len(self.df) < 50:
            return
        
        # Obtener precio actual
        tick = mt5.symbol_info_tick("XAUUSD")
        self.current_price = tick.bid if tick else self.df.iloc[-1]['close']
        
        # Analizar niveles S/R con MTF
        all_levels = self.sr_system.analyze_all_timeframes(self.current_price)
        self.levels = self.sr_system.find_confluence_levels(all_levels, self.current_price)
        
        # Obtener señal actual
        self.current_signal = self.sr_system.get_signal(self.df, self.current_price)
        
        # Limpiar gráfico
        self.ax.clear()
        
        # Re-configurar estilo después de clear
        self.ax.set_facecolor('#1a1a1a')
        self.ax.grid(True, alpha=0.12, color='#505050', linestyle='-', linewidth=0.8, which='major')
        self.ax.grid(True, alpha=0.05, color='#404040', linestyle='-', linewidth=0.4, which='minor')
        self.ax.minorticks_on()
        self.ax.set_xlabel('Tiempo (Barras) →', color='#e0e0e0', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Precio XAUUSD (USD)', color='#e0e0e0', fontsize=12, fontweight='bold')
        self.ax.tick_params(colors='#c0c0c0', labelsize=10, width=1.8, length=7)
        
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#505050')
            spine.set_linewidth(2)
        
        # Obtener últimas 100 barras para visualización
        df_plot = self.df.tail(100).reset_index(drop=True)
        
        # Dibujar componentes EN ORDEN correcto
        # 1. Niveles S/R (fondo)
        self.draw_sr_levels(self.levels, df_plot, self.current_price)
        
        # 2. Líneas EMA
        self.draw_ema_lines(df_plot)
        
        # 3. Velas japonesas (encima de todo menos señales)
        self.draw_candlesticks(df_plot)
        
        # 4. Señal actual (al frente)
        if self.current_signal:
            self.draw_current_signal(self.current_signal, df_plot)
        
        # Ajustar límites Y con margen
        y_min = df_plot['low'].min()
        y_max = df_plot['high'].max()
        y_range = y_max - y_min
        self.ax.set_ylim(y_min - y_range * 0.15, y_max + y_range * 0.15)
        
        # Título dinámico
        timestamp = datetime.now().strftime("%H:%M:%S")
        title = f"XAUUSD M30 | Precio: ${self.current_price:.2f} | {timestamp}"
        self.ax.set_title(title, color='#FFD700', fontsize=14, fontweight='bold', pad=15)
        
        # Redibujar
        self.canvas.draw()
        
        # Actualizar panel de información
        self.update_info_panel()
    
    def update_info_panel(self):
        """Actualiza el panel de información lateral"""
        # Actualizar precio
        self.price_label.config(text=f"Precio: ${self.current_price:.2f}")
        
        # Actualizar señal
        if self.current_signal:
            signal_type = " BUY" if self.current_signal['signal'] == 1 else " SELL"
            self.signal_label.config(text=f"Señal: {signal_type}", 
                                    fg="#00ff66" if self.current_signal['signal'] == 1 else "#ff3366")
            
            conf_pct = self.current_signal['confidence'] * 100
            self.confidence_label.config(text=f"Confianza: {conf_pct:.1f}%")
        else:
            self.signal_label.config(text="Señal: Sin señal", fg="#888888")
            self.confidence_label.config(text="Confianza: 0%")
        
        # Actualizar tabla de niveles
        for item in self.levels_tree.get_children():
            self.levels_tree.delete(item)
        
        for level_data in self.levels[:12]:
            level_type = " RESIST" if level_data['type'] == 'resistance' else " SUPPORT"
            level_price = f"${level_data['level']:.2f}"
            touches = level_data.get('total_touches', level_data.get('touches', 1))
            
            self.levels_tree.insert("", "end", values=(level_type, level_price, touches))
    
    def auto_update_loop(self):
        """Loop de auto-actualización"""
        if self.auto_update_var.get():
            self.update_chart()
        
        # Programar siguiente actualización (5 segundos)
        self.window.after(5000, self.auto_update_loop)
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   VENTANA DE AUTONOMÍA ML v5.2                           ║
║                                                                          ║
║  🆕 MODIFICADO: Muestra solo operaciones ganadoras >= threshold          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime


class MLAutonomyWindow:
    """
    Ventana separada para mostrar métricas de autonomía ML
    
    🆕 v5.2: Cuenta solo operaciones ganadoras >= $5 (configurable desde GUI)
    """
    
    def __init__(self, parent, bot_queue):
        self.window = tk.Toplevel(parent)
        self.window.title("🤖 Panel de Autonomía ML v5.2")
        self.window.geometry("1200x800")
        self.window.configure(bg="#1e1e1e")
        
        self.bot_queue = bot_queue
        
        self.setup_ui()
        self.update_autonomy_data()
    
    def setup_ui(self):
        # HEADER
        header = tk.Frame(self.window, bg="#2d2d2d", height=80)
        header.pack(fill=tk.X, padx=10, pady=8)
        header.pack_propagate(False)
        
        title = tk.Label(header, text="🤖 PANEL DE AUTONOMÍA ML",
                        font=("Arial", 18, "bold"), bg="#2d2d2d", fg="#00ff00")
        title.pack(pady=5)
        
        self.mode_label = tk.Label(header, text="🧠 MODO: APRENDIENDO...",
                                  font=("Arial", 12, "bold"), bg="#2d2d2d", fg="#ffaa00")
        self.mode_label.pack()
        
        # CONTENEDOR PRINCIPAL
        main_container = tk.Frame(self.window, bg="#1e1e1e")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # IZQUIERDA: Progreso y Estado
        left_panel = tk.Frame(main_container, bg="#2d2d2d", width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        left_panel.pack_propagate(False)
        
        # DERECHA: Decisiones
        right_panel = tk.Frame(main_container, bg="#2d2d2d")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # === PANEL IZQUIERDO ===
        
        # Progreso de Autonomía
        progress_frame = tk.LabelFrame(left_panel, text="📊 PROGRESO DE AUTONOMÍA",
                                      font=("Arial", 11, "bold"), bg="#2d2d2d",
                                      fg="#ffffff", padx=10, pady=8)
        progress_frame.pack(fill=tk.X, padx=8, pady=8)
        
        # 🆕 MODIFICADO: Texto cambiado a "Ops ganadoras"
        self.progress_label = tk.Label(progress_frame, text="Ops ganadoras: 0/100",
                                      font=("Arial", 10), bg="#2d2d2d", fg="#ffffff")
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate',
                                           length=350, maximum=100)
        self.progress_bar.pack(pady=5)
        
        self.confidence_label = tk.Label(progress_frame, text="Confianza: 0%",
                                        font=("Arial", 9), bg="#2d2d2d", fg="#aaaaaa")
        self.confidence_label.pack(pady=2)
        
        self.eta_label = tk.Label(progress_frame, text="ETA: Calculando...",
                                 font=("Arial", 9), bg="#2d2d2d", fg="#aaaaaa")
        self.eta_label.pack(pady=2)
        
        # 🆕 NUEVO: Mostrar threshold actual
        self.threshold_label = tk.Label(progress_frame, text="Profit mínimo: $5.00",
                                       font=("Arial", 9), bg="#2d2d2d", fg="#aaaaaa")
        self.threshold_label.pack(pady=2)
        
        # Fases del Aprendizaje
        phases_frame = tk.LabelFrame(left_panel, text="🔄 FASES DE APRENDIZAJE",
                                    font=("Arial", 11, "bold"), bg="#2d2d2d",
                                    fg="#ffffff", padx=10, pady=8)
        phases_frame.pack(fill=tk.X, padx=8, pady=8)
        
        # 🆕 MODIFICADO: Texto cambiado a "ops ganadoras"
        self.phase1_label = tk.Label(phases_frame, text="🟢 FASE 1: Recopilando datos (0-50 ops ganadoras)",
                                     font=("Arial", 9), bg="#2d2d2d", fg="#44ff44", anchor='w')
        self.phase1_label.pack(fill=tk.X, pady=2)
        
        self.phase2_label = tk.Label(phases_frame, text="⚪ FASE 2: Aprendiendo patrones (50-100 ops ganadoras)",
                                     font=("Arial", 9), bg="#2d2d2d", fg="#666666", anchor='w')
        self.phase2_label.pack(fill=tk.X, pady=2)
        
        self.phase3_label = tk.Label(phases_frame, text="⚪ FASE 3: AUTÓNOMO (100+ ops ganadoras)",
                                     font=("Arial", 9), bg="#2d2d2d", fg="#666666", anchor='w')
        self.phase3_label.pack(fill=tk.X, pady=2)
        
        # Parámetros Aprendidos
        params_frame = tk.LabelFrame(left_panel, text="⚙️ PARÁMETROS APRENDIDOS",
                                    font=("Arial", 11, "bold"), bg="#2d2d2d",
                                    fg="#ffffff", padx=10, pady=8)
        params_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        params_scroll = tk.Frame(params_frame, bg="#2d2d2d")
        params_scroll.pack(fill=tk.BOTH, expand=True)
        
        self.params_text = scrolledtext.ScrolledText(params_scroll, height=12,
                                                     bg="#1e1e1e", fg="#00ff00",
                                                     font=("Consolas", 9), wrap=tk.WORD)
        self.params_text.pack(fill=tk.BOTH, expand=True)
        
        # === PANEL DERECHO ===
        
        # Decisiones ML Recientes
        decisions_frame = tk.LabelFrame(right_panel, text="🧠 DECISIONES ML RECIENTES",
                                       font=("Arial", 11, "bold"), bg="#2d2d2d",
                                       fg="#ffffff", padx=10, pady=8)
        decisions_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.decisions_text = scrolledtext.ScrolledText(decisions_frame, height=20,
                                                       bg="#1e1e1e", fg="#ffffff",
                                                       font=("Consolas", 9), wrap=tk.WORD)
        self.decisions_text.pack(fill=tk.BOTH, expand=True)
        
        # Botones de control
        control_frame = tk.Frame(self.window, bg="#2d2d2d", height=60)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        btn_refresh = tk.Button(control_frame, text="🔄 Actualizar",
                               font=("Arial", 10, "bold"), bg="#44ff44", fg="#000000",
                               command=self.request_autonomy_update, cursor="hand2", width=15)
        btn_refresh.pack(side=tk.LEFT, padx=10)
        
        btn_reset = tk.Button(control_frame, text="🔧 Resetear Autonomía",
                             font=("Arial", 10, "bold"), bg="#ffaa00", fg="#000000",
                             command=self.reset_autonomy, cursor="hand2", width=18)
        btn_reset.pack(side=tk.LEFT, padx=10)
        
        self.auto_update_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(control_frame, text="Auto-actualizar cada 5s",
                                   variable=self.auto_update_var, font=("Arial", 9),
                                   bg="#2d2d2d", fg="#ffffff", selectcolor="#1e1e1e")
        auto_check.pack(side=tk.RIGHT, padx=10)
    
    def request_autonomy_update(self):
        if self.bot_queue:
            self.bot_queue.put({'type': 'request_autonomy_data'})
    
    def reset_autonomy(self):
        response = messagebox.askyesno("Confirmar Reset",
                                      "¿Resetear el aprendizaje ML? Se perderán los parámetros aprendidos.")
        if response and self.bot_queue:
            self.bot_queue.put({'type': 'reset_autonomy'})
            messagebox.showinfo("Reset Completado", "El sistema ML ha sido reseteado a modo manual.")
    
    def update_progress(self, autonomy_data):
        """🆕 MODIFICADO: Muestra "Ops ganadoras" en lugar de "Operaciones"""
        ops = autonomy_data.get("operations", 0)
        threshold = autonomy_data.get("threshold", 100)
        confidence = autonomy_data.get("confidence", 0)
        is_active = autonomy_data.get("active", False)
        min_profit = autonomy_data.get("min_profit_threshold", 5.0)
        
        # 🆕 MODIFICADO: Labels actualizados
        self.progress_label.config(text=f"Ops ganadoras: {ops}/{threshold}")
        self.progress_bar['value'] = min(100, (ops / threshold) * 100)
        self.confidence_label.config(text=f"Confianza: {confidence:.1f}%")
        self.threshold_label.config(text=f"Profit mínimo: ${min_profit:.2f}")
        
        if is_active:
            self.mode_label.config(text="🤖 MODO: AUTÓNOMO ✅", fg="#44ff44")
            self.eta_label.config(text="Estado: Completamente autónomo")
            self.phase3_label.config(text="🔵 FASE 3: AUTÓNOMO (100+ ops ganadoras) ✅", fg="#00aaff")
        else:
            remaining = threshold - ops
            self.eta_label.config(text=f"Restantes: {remaining} ops ganadoras")
            
            if ops < 50:
                self.phase1_label.config(text="🟢 FASE 1: Recopilando datos (0-50 ops ganadoras) ✅", fg="#44ff44")
            elif ops < 100:
                self.phase1_label.config(text="✅ FASE 1: Completada", fg="#888888")
                self.phase2_label.config(text="🟡 FASE 2: Aprendiendo patrones (50-100 ops ganadoras) ✅", fg="#ffaa00")
    
    def update_learned_params(self, params_data):
        self.params_text.delete(1.0, tk.END)
        
        self.params_text.insert(tk.END, "╔═══ TRAILING STOP ═══╗\n", "header")
        trailing = params_data.get("trailing_stop", {})
        initial_trailing = params_data.get("initial_trailing", {})
        
        self.params_text.insert(tk.END, f"  Manual:        {initial_trailing.get('activation_pips', 30)} pips activación\n")
        self.params_text.insert(tk.END, f"  ML Ajustado:   {trailing.get('activation_pips', 30)} pips\n", "value")
        self.params_text.insert(tk.END, f"  Distancia:     {trailing.get('distance_pips', 20)} pips\n")
        self.params_text.insert(tk.END, f"  Modo:          {trailing.get('mode', 'manual').upper()}\n\n")
        
        self.params_text.insert(tk.END, "╔═══ BREAKEVEN ═══╗\n", "header")
        breakeven = params_data.get("breakeven", {})
        
        self.params_text.insert(tk.END, f"  Activación:    +{breakeven.get('activation_pips', 40)} pips\n", "value")
        self.params_text.insert(tk.END, f"  Seguridad:     +{breakeven.get('safety_pips', 5)} pips\n")
        self.params_text.insert(tk.END, f"  Modo:          {breakeven.get('mode', 'manual').upper()}\n")
        
        self.params_text.tag_config("header", foreground="#00ff00", font=("Consolas", 9, "bold"))
        self.params_text.tag_config("value", foreground="#FFD700")
    
    def update_decisions_log(self, decisions):
        self.decisions_text.delete(1.0, tk.END)
        
        if not decisions:
            self.decisions_text.insert(tk.END, "No hay decisiones ML todavía...\n")
            return
        
        for decision in reversed(decisions[-10:]):
            timestamp = decision.get("timestamp", "")
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            
            param = decision.get("parameter", "unknown")
            reason = decision.get("reason", "")
            
            self.decisions_text.insert(tk.END, f"[{time_str}] ", "time")
            self.decisions_text.insert(tk.END, f"{param.upper()}\n", "param")
            self.decisions_text.insert(tk.END, f"  📊 {reason}\n\n", "reason")
        
        self.decisions_text.tag_config("time", foreground="#aaaaaa")
        self.decisions_text.tag_config("param", foreground="#00ff00", font=("Consolas", 9, "bold"))
        self.decisions_text.tag_config("reason", foreground="#ffffff")
    
    def update_autonomy_data(self):
        if self.auto_update_var.get():
            self.request_autonomy_update()
        
        self.window.after(5000, self.update_autonomy_data)
    
    def update_all_data(self, data):
        autonomy_status = data.get("autonomy_status", {})
        learned_params = data.get("learned_params", {})
        initial_params = data.get("initial_params", {})
        recent_decisions = data.get("recent_decisions", [])
        
        self.update_progress(autonomy_status)
        
        params_combined = learned_params.copy()
        params_combined["initial_trailing"] = initial_params.get("trailing_stop", {})
        self.update_learned_params(params_combined)
        
        self.update_decisions_log(recent_decisions)
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   PANEL ML DASHBOARD v5.2                                ║
║                                                                          ║
║  🆕 MODIFICADO: Muestra "Ops ganadoras" en lugar de "Ops totales"       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk


class MLDashboardPanel:
    """Panel compacto de dashboard ML con contador de rotación"""
    
    def __init__(self, parent):
        self.frame = tk.LabelFrame(parent, text="🧠 MACHINE LEARNING",
                                   font=("Arial", 10, "bold"), bg="#2d2d2d",
                                   fg="#00ff00", padx=8, pady=6)
        self.frame.pack(fill=tk.X, padx=8, pady=6)
        
        self.setup_ui()
    
    def setup_ui(self):
        model_frame = tk.Frame(self.frame, bg="#2d2d2d")
        model_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(model_frame, text="🤖 Modelo:", font=("Arial", 9, "bold"),
                bg="#2d2d2d", fg="#ffffff", width=10, anchor='w').pack(side=tk.LEFT)
        
        self.active_model_label = tk.Label(model_frame, text="Random Forest",
                                          font=("Arial", 9), bg="#2d2d2d", fg="#00ff00")
        self.active_model_label.pack(side=tk.LEFT, padx=5)
        
        # ⭐ NUEVO: Contador de rotación
        rotation_frame = tk.Frame(self.frame, bg="#2d2d2d")
        rotation_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(rotation_frame, text="🔄 Rotación:", font=("Arial", 8, "bold"),
                bg="#2d2d2d", fg="#aaaaaa", width=10, anchor='w').pack(side=tk.LEFT)
        
        self.rotation_counter_label = tk.Label(rotation_frame, text="0/10 ops totales",
                                               font=("Arial", 8), bg="#2d2d2d", fg="#ffaa00")
        self.rotation_counter_label.pack(side=tk.LEFT, padx=5)
        
        self.next_model_label = tk.Label(rotation_frame, text="→ GB",
                                         font=("Arial", 8), bg="#2d2d2d", fg="#888888")
        self.next_model_label.pack(side=tk.LEFT, padx=2)
        
        filter_frame = tk.LabelFrame(self.frame, text="🎓 Aprendizaje",
                                    font=("Arial", 9, "bold"), bg="#2d2d2d",
                                    fg="#ffffff", padx=6, pady=4)
        filter_frame.pack(fill=tk.X, pady=3)
        
        filter_label = tk.Label(filter_frame,
                               text="Solo trades rentables (≥$10)",
                               font=("Arial", 8),
                               bg="#2d2d2d",
                               fg="#44ff44")
        filter_label.pack(pady=2)
        
        # Métricas
        metrics_frame = tk.LabelFrame(self.frame, text="📊 Métricas",
                                     font=("Arial", 9, "bold"), bg="#2d2d2d",
                                     fg="#ffffff", padx=6, pady=4)
        metrics_frame.pack(fill=tk.X, pady=3)
        
        row1 = tk.Frame(metrics_frame, bg="#2d2d2d")
        row1.pack(fill=tk.X, pady=1)
        
        tk.Label(row1, text="Ops:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=8, anchor='w').pack(side=tk.LEFT)
        self.total_trades_label = tk.Label(row1, text="0", font=("Arial", 8, "bold"),
                                          bg="#2d2d2d", fg="#ffffff", width=6, anchor='w')
        self.total_trades_label.pack(side=tk.LEFT)
        
        tk.Label(row1, text="Win:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=6, anchor='w').pack(side=tk.LEFT, padx=3)
        self.win_rate_label = tk.Label(row1, text="0%", font=("Arial", 8, "bold"),
                                       bg="#2d2d2d", fg="#44ff44", width=6, anchor='w')
        self.win_rate_label.pack(side=tk.LEFT)
        
        row2 = tk.Frame(metrics_frame, bg="#2d2d2d")
        row2.pack(fill=tk.X, pady=1)
        
        tk.Label(row2, text="Prec:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=8, anchor='w').pack(side=tk.LEFT)
        self.prediction_acc_label = tk.Label(row2, text="0%", font=("Arial", 8, "bold"),
                                            bg="#2d2d2d", fg="#00ffff", width=6, anchor='w')
        self.prediction_acc_label.pack(side=tk.LEFT)
        
        tk.Label(row2, text="$:", font=("Arial", 8),
                bg="#2d2d2d", fg="#aaaaaa", width=6, anchor='w').pack(side=tk.LEFT, padx=3)
        self.total_profit_label = tk.Label(row2, text="$0", font=("Arial", 8, "bold"),
                                          bg="#2d2d2d", fg="#FFD700", width=6, anchor='w')
        self.total_profit_label.pack(side=tk.LEFT)
        
        # Comparación de modelos
        comparison_frame = tk.LabelFrame(self.frame, text="🏆 Modelos",
                                        font=("Arial", 9, "bold"), bg="#2d2d2d",
                                        fg="#ffffff", padx=6, pady=4)
        comparison_frame.pack(fill=tk.X, pady=3)
        
        style = ttk.Style()
        style.configure("ML.Treeview", background="#1e1e1e", foreground="white",
                       fieldbackground="#1e1e1e", font=("Consolas", 9), rowheight=20)
        style.configure("ML.Treeview.Heading", font=("Arial", 9, "bold"))
        
        self.models_tree = ttk.Treeview(comparison_frame,
                                       columns=("✓", "Modelo", "Prec", "$"),
                                       show="headings", height=3, style="ML.Treeview")
        
        self.models_tree.heading("✓", text="")
        self.models_tree.heading("Modelo", text="Modelo")
        self.models_tree.heading("Prec", text="Prec")
        self.models_tree.heading("$", text="$")
        
        self.models_tree.column("✓", width=18, anchor='center')
        self.models_tree.column("Modelo", width=100, anchor='w')
        self.models_tree.column("Prec", width=45, anchor='center')
        self.models_tree.column("$", width=55, anchor='center')
        
        self.models_tree.pack(fill=tk.X)
    
    def update_ml_status(self, ml_data):
        """⭐ ACTUALIZADO: Muestra precisión en tiempo real + contador de rotación GLOBAL"""
        performance = ml_data.get("performance")
        models = ml_data.get("models", {})
        active_model = ml_data.get("active_model", "Unknown")
        rotation_status = ml_data.get("rotation_status", {})
        
        model_names = {
            "random_forest": "Random Forest",
            "gradient_boost": "Gradient Boost",
            "neural_net": "Neural Network"
        }
        
        short_names = {
            "random_forest": "RF",
            "gradient_boost": "GB",
            "neural_net": "NN"
        }
        
        self.active_model_label.config(text=model_names.get(active_model, active_model))
        
        # ⭐ NUEVO: Actualizar contador de rotación GLOBAL
        if rotation_status:
            current_count = rotation_status.get('current_count', 0)
            rotate_every = rotation_status.get('rotate_every', 10)
            next_model = rotation_status.get('next_model', 'unknown')
            
            self.rotation_counter_label.config(text=f"{current_count}/{rotate_every} ops totales")
            self.next_model_label.config(text=f"→ {short_names.get(next_model, next_model)}")
            
            # Cambiar color según proximidad a rotación
            if current_count >= rotate_every - 2:
                self.rotation_counter_label.config(fg="#ff4444")  # Rojo: cerca de rotar
            elif current_count >= rotate_every - 5:
                self.rotation_counter_label.config(fg="#ffaa00")  # Naranja: acercándose
            else:
                self.rotation_counter_label.config(fg="#44ff44")  # Verde: lejos
        
        if performance:
            self.total_trades_label.config(text=str(performance.get("total_trades", 0)))
            
            win_rate = performance.get("win_rate", 0)
            self.win_rate_label.config(text=f"{win_rate:.0f}%")
            if win_rate >= 60:
                self.win_rate_label.config(fg="#44ff44")
            elif win_rate >= 50:
                self.win_rate_label.config(fg="#ffaa00")
            else:
                self.win_rate_label.config(fg="#ff4444")
            
            pred_acc = performance.get("prediction_accuracy", 0)
            self.prediction_acc_label.config(text=f"{pred_acc:.0f}%")
            
            total_profit = performance.get("total_profit", 0)
            self.total_profit_label.config(text=f"${total_profit:.0f}")
            if total_profit > 0:
                self.total_profit_label.config(fg="#44ff44")
            else:
                self.total_profit_label.config(fg="#ff4444")
        
        # ⭐ ACTUALIZAR TABLA DE MODELOS CON PRECISIÓN EN TIEMPO REAL
        for item in self.models_tree.get_children():
            self.models_tree.delete(item)
        
        for model_name, model_data in models.items():
            is_active = model_data.get("active", False)
            perf = model_data.get("performance", {})
            
            estado = "✓" if is_active else ""
            accuracy = perf.get("accuracy", 0)
            profit = perf.get("profit", 0)
            
            tag = 'active' if is_active else 'inactive'
            
            self.models_tree.insert("", "end", values=(
                estado,
                short_names.get(model_name, model_name[:8]),
                f"{accuracy:.0f}%",
                f"${profit:.0f}"
            ), tags=(tag,))
        
        self.models_tree.tag_configure('active', background='#1a4a1a')
        self.models_tree.tag_configure('inactive', background='#2d2d2d')
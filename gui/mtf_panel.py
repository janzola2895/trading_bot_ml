"""
╔══════════════════════════════════════════════════════════════════════════╗
║          PANEL MTF v7.0 SIMPLIFICADO - Solo Checkboxes                  ║
║                                                                          ║
║  Panel minimalista con solo selección de temporalidades                 ║
║  Sin mostrar estados individuales - solo resultado final                ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk


class MTFDashboardPanel:
    """Panel simplificado MTF - Solo checkboxes y resultado"""
    
    def __init__(self, parent, message_queue=None):
        self.message_queue = message_queue
        
        self.frame = tk.LabelFrame(parent, text="📊 ANÁLISIS MTF",
                                   font=("Arial", 10, "bold"), bg="#2d2d2d",
                                   fg="#00ff00", padx=8, pady=6)
        self.frame.pack(fill=tk.X, padx=8, pady=6)
        
        # Variables de checkboxes
        self.tf_vars = {
            'M15': tk.BooleanVar(value=False),
            'M30': tk.BooleanVar(value=False),
            'H1': tk.BooleanVar(value=False),   
            'H4': tk.BooleanVar(value=False),   
            'D1': tk.BooleanVar(value=True),    # ✅ Activo por defecto
            'W1': tk.BooleanVar(value=False)    
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        # === SELECCIÓN DE TEMPORALIDADES ===
        selection_frame = tk.LabelFrame(self.frame, text="🎯 Temporalidades Activas",
                                       font=("Arial", 9, "bold"), bg="#2d2d2d",
                                       fg="#FFD700", padx=6, pady=4)
        selection_frame.pack(fill=tk.X, pady=3)
        
        # Grid de checkboxes (2 columnas)
        checkbox_container = tk.Frame(selection_frame, bg="#2d2d2d")
        checkbox_container.pack(fill=tk.X, pady=2)
        
        timeframes = ['M15', 'M30', 'H1', 'H4', 'D1', 'W1']
        
        for idx, tf in enumerate(timeframes):
            row = idx // 2
            col = idx % 2
            
            check = tk.Checkbutton(checkbox_container, 
                                  text=f"📊 {tf}",
                                  variable=self.tf_vars[tf],
                                  font=("Arial", 9, "bold"),
                                  bg="#2d2d2d", 
                                  fg="#ffffff",
                                  selectcolor="#1e1e1e",
                                  activebackground="#2d2d2d",
                                  activeforeground="#00ff00")
            check.grid(row=row, column=col, sticky='w', padx=8, pady=2)
        
        # Botón aplicar configuración
        apply_btn = tk.Button(selection_frame,
                             text="✅ Aplicar Configuración MTF",
                             font=("Arial", 8, "bold"),
                             bg="#44ff44",
                             fg="#000000",
                             command=self.on_config_change,
                             cursor="hand2")
        apply_btn.pack(pady=4)
        
        # === RESULTADO FINAL ===
        result_frame = tk.Frame(self.frame, bg="#2d2d2d")
        result_frame.pack(fill=tk.X, pady=4)
        
        self.result_label = tk.Label(result_frame, text="⛔ SIN ALINEACIÓN",
                                     font=("Arial", 9, "bold"), bg="#2d2d2d", fg="#ff4444")
        self.result_label.pack()
        
        # Regla dinámica
        self.rule_label = tk.Label(self.frame, 
                                   text="Regla: TODAS las TFs activas deben coincidir",
                                   font=("Arial", 7), bg="#2d2d2d", fg="#888888")
        self.rule_label.pack(pady=2)
    
    def on_config_change(self):
        """Se ejecuta cuando cambia la configuración"""
        active_tfs = self.get_active_timeframes()
        
        # 🔧 NUEVO: Limpiar resultado anterior inmediatamente
        self.result_label.config(
            text="⏳ ACTUALIZANDO CONFIGURACIÓN...",
            fg="#ffaa00"
        )
        
        # Actualizar texto de regla
        if len(active_tfs) == 0:
            rule_text = "⚠️ Sin temporalidades activas - TODO bloqueado"
            self.rule_label.config(text=rule_text, fg="#ff4444")
        elif len(active_tfs) == 1:
            rule_text = f"Regla: Solo {active_tfs[0]} decide"
            self.rule_label.config(text=rule_text, fg="#00aaff")
        else:
            tfs_text = '+'.join(active_tfs)
            rule_text = f"Regla: {tfs_text} deben coincidir TODAS"
            self.rule_label.config(text=rule_text, fg="#888888")
        
        # Enviar configuración al bot si hay queue
        if self.message_queue:
            self.message_queue.put({
                'type': 'mtf_config',
                'active_timeframes': active_tfs
            })
            
    def update_mtf_data(self, mtf_analysis):
        """Actualiza el panel con datos de análisis MTF"""
        if not mtf_analysis:
            return
        
        # Actualizar solo resultado final
        if mtf_analysis.get('approved', False):
            direction = mtf_analysis.get('direction', 'unknown').upper()
            emoji = "🟢" if mtf_analysis.get('direction') == 'buy' else "🔴"
            
            # Obtener temporalidades que coincidieron
            aligned_tfs = mtf_analysis.get('aligned_timeframes', [])
            tfs_text = '+'.join(aligned_tfs)
            
            self.result_label.config(
                text=f"{emoji} {direction} APROBADO ✅ ({tfs_text})", 
                fg="#44ff44"
            )
        else:
            # Mostrar estado de cada TF activo
            active_tfs = mtf_analysis.get('active_timeframes', [])
            tf_detail = mtf_analysis.get('timeframes_detail', {})
            
            if len(active_tfs) == 0:
                self.result_label.config(
                    text="⚠️ Sin temporalidades activas",
                    fg="#ffaa00"
                )
            else:
                # Mostrar resumen de bias
                bias_summary = []
                for tf in active_tfs:
                    if tf in tf_detail:
                        bias = tf_detail[tf].get('bias', 'neutral')[:4].upper()
                        bias_summary.append(f"{tf}:{bias}")
                
                summary_text = " / ".join(bias_summary)
                
                self.result_label.config(
                    text=f"⛔ SIN ALINEACIÓN ({summary_text})", 
                    fg="#ff4444"
                )
    
    def get_active_timeframes(self):
        """Retorna lista de temporalidades activas"""
        return [tf for tf, var in self.tf_vars.items() if var.get()]
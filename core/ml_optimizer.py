"""
╔══════════════════════════════════════════════════════════════════════════╗
║            SISTEMA DE OPTIMIZACIÓN ML AUTÓNOMO v5.2                      ║
║                                                                          ║
║  🆕 MODIFICADO: Cuenta solo operaciones ganadoras >= $5 (configurable)  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime
from config import (
    DATA_DIR, 
    MIN_PROFIT_FOR_AUTONOMY,
    AUTONOMY_THRESHOLD,
    TRAILING_ENABLED, TRAILING_ACTIVATION_PIPS, TRAILING_DISTANCE_PIPS,
    BREAKEVEN_ENABLED, BREAKEVEN_ACTIVATION_PIPS, BREAKEVEN_SAFETY_PIPS
)


class MLParameterOptimizer:
    """
    Sistema que aprende y optimiza parámetros automáticamente
    
    🆕 v5.2: Solo cuenta operaciones ganadoras >= threshold configurable
    """
    
    def __init__(self, data_dir=DATA_DIR, min_profit_threshold=MIN_PROFIT_FOR_AUTONOMY):
        self.data_dir = data_dir
        self.optimizer_file = os.path.join(data_dir, "ml_optimizer.json")
        
        # 🆕 Umbral de profit para contar operación (configurable)
        self.min_profit_for_autonomy = min_profit_threshold
        
        self.initial_params = {
            "trailing_stop": {
                "enabled": TRAILING_ENABLED,
                "activation_pips": TRAILING_ACTIVATION_PIPS,
                "distance_pips": TRAILING_DISTANCE_PIPS,
                "mode": "manual"
            },
            "breakeven": {
                "enabled": BREAKEVEN_ENABLED,
                "activation_pips": BREAKEVEN_ACTIVATION_PIPS,
                "safety_pips": BREAKEVEN_SAFETY_PIPS,
                "mode": "manual"
            },
            "lot_management": {
                "mode": "fixed",
                "fixed_lot": 0.03,
                "risk_percentage": 1.0,
                "mode_status": "manual"
            }
        }
        
        self.learned_params = self.initial_params.copy()
        
        self.learning_stats = {
            "total_operations": 0,  # 🆕 Ahora cuenta solo ganadoras >= threshold
            "autonomy_threshold": AUTONOMY_THRESHOLD,
            "autonomy_active": False,
            "confidence_level": 0.0,
            "decisions_made": [],
            "min_profit_threshold": self.min_profit_for_autonomy  # 🆕 Guardamos el threshold
        }
        
        self.load_optimizer_data()
    
    def load_optimizer_data(self):
        if os.path.exists(self.optimizer_file):
            try:
                with open(self.optimizer_file, 'r') as f:
                    data = json.load(f)
                    self.learned_params = data.get('learned_params', self.initial_params)
                    self.learning_stats = data.get('learning_stats', self.learning_stats)
                    
                    # 🆕 Actualizar threshold si cambió
                    self.learning_stats["min_profit_threshold"] = self.min_profit_for_autonomy
            except:
                pass
    
    def save_optimizer_data(self):
        try:
            data = {
                'initial_params': self.initial_params,
                'learned_params': self.learned_params,
                'learning_stats': self.learning_stats,
                'last_update': datetime.now().isoformat()
            }
            with open(self.optimizer_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error guardando optimizer: {e}")
    
    def update_operation_count(self, profit):
        """
        🆕 MODIFICADO: Solo cuenta operaciones ganadoras >= threshold
        
        Args:
            profit: Profit de la operación cerrada
        
        Returns:
            bool: True si se activó autonomía
        """
        # 🆕 Solo incrementar si profit >= threshold
        if profit < self.min_profit_for_autonomy:
            return False
        
        self.learning_stats["total_operations"] += 1
        ops = self.learning_stats["total_operations"]
        print(f"✅ Operación #{ops} CONTADA para autonomía (profit: ${profit:.2f})")

        threshold = self.learning_stats["autonomy_threshold"]
        self.learning_stats["confidence_level"] = min(100, (ops / threshold) * 100)
        
        if ops >= threshold and not self.learning_stats["autonomy_active"]:
            self.learning_stats["autonomy_active"] = True
            self.save_optimizer_data()
            return True
        
        self.save_optimizer_data()
        return False
    
    def update_threshold(self, new_threshold):
        """
        🆕 Actualiza el umbral de profit mínimo
        
        Args:
            new_threshold: Nuevo umbral en USD
        """
        self.min_profit_for_autonomy = new_threshold
        self.learning_stats["min_profit_threshold"] = new_threshold
        self.save_optimizer_data()
    
    def optimize_trailing_stop(self, market_conditions, historical_performance):
        if not self.learning_stats["autonomy_active"]:
            return self.initial_params["trailing_stop"]
        
        atr = market_conditions.get("atr", 2.0)
        volatility = market_conditions.get("volatility", "normal")
        
        if volatility == "high" or atr > 2.5:
            activation_pips = int(35 + (atr - 2.5) * 10)
            distance_pips = int(25 + (atr - 2.5) * 5)
            reason = f"Alta volatilidad (ATR={atr:.2f})"
        else:
            activation_pips = self.initial_params["trailing_stop"]["activation_pips"]
            distance_pips = self.initial_params["trailing_stop"]["distance_pips"]
            reason = "Condiciones normales"
        
        decision = {
            "timestamp": datetime.now().isoformat(),
            "parameter": "trailing_stop",
            "new_value": {
                "enabled": True,
                "activation_pips": activation_pips,
                "distance_pips": distance_pips,
                "mode": "autonomous"
            },
            "reason": reason
        }
        
        self.learning_stats["decisions_made"].append(decision)
        self.learned_params["trailing_stop"] = decision["new_value"]
        self.save_optimizer_data()
        
        return self.learned_params["trailing_stop"]
    
    def optimize_breakeven(self, market_conditions, historical_performance):
        if not self.learning_stats["autonomy_active"]:
            return self.initial_params["breakeven"]
        
        breakeven_ops = [op for op in historical_performance 
                        if op.get("breakeven_triggered", False)]
        
        if len(breakeven_ops) >= 10:
            activation_pips = 32
            safety_pips = 5
            reason = "Optimizado según histórico"
        else:
            activation_pips = self.initial_params["breakeven"]["activation_pips"]
            safety_pips = self.initial_params["breakeven"]["safety_pips"]
            reason = "Parámetros iniciales"
        
        decision = {
            "timestamp": datetime.now().isoformat(),
            "parameter": "breakeven",
            "new_value": {
                "enabled": True,
                "activation_pips": activation_pips,
                "safety_pips": safety_pips,
                "mode": "autonomous"
            },
            "reason": reason
        }
        
        self.learning_stats["decisions_made"].append(decision)
        self.learned_params["breakeven"] = decision["new_value"]
        self.save_optimizer_data()
        
        return self.learned_params["breakeven"]
    
    def get_current_params(self):
        if self.learning_stats["autonomy_active"]:
            return self.learned_params
        return self.initial_params
    
    def get_autonomy_status(self):
        """
        🆕 MODIFICADO: Retorna estado con info del threshold
        """
        return {
            "active": self.learning_stats["autonomy_active"],
            "operations": self.learning_stats["total_operations"],
            "threshold": self.learning_stats["autonomy_threshold"],
            "confidence": self.learning_stats["confidence_level"],
            "progress_percentage": min(100, (self.learning_stats["total_operations"] / self.learning_stats["autonomy_threshold"]) * 100),
            "min_profit_threshold": self.min_profit_for_autonomy  # 🆕
        }
    
    def get_recent_decisions(self, limit=10):
        decisions = self.learning_stats["decisions_made"]
        return decisions[-limit:] if len(decisions) > limit else decisions
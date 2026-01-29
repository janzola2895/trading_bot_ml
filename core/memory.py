"""
╔══════════════════════════════════════════════════════════════════════════╗
║                   SISTEMA DE MEMORIA Y TRACKING v5.2                     ║
║                                                                          ║
║  🆕 MODIFICADO: Método para obtener estadísticas por estrategia          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime
from config import DATA_DIR


class TradingMemory:
    """Sistema de memoria para almacenar operaciones"""
    
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.memory_file = os.path.join(data_dir, "trading_memory.json")
        
        # 🆕 SOLUCIÓN: Crear carpeta si no existe
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"✅ Carpeta '{self.data_dir}' creada")
        self.memory = self.load_memory()
        
    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                return {"trades": [], "metadata": {"created": datetime.now().isoformat()}}
        return {"trades": [], "metadata": {"created": datetime.now().isoformat()}}
    
    def save_memory(self):
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando memoria: {e}")
            return False
    
    def add_trade_entry(self, features, signal, confidence, market_state, strategy="ml",
                       trailing_params=None, breakeven_params=None, lot_params=None,
                       htf_bias=None):
        trade_entry = {
            "id": f"trade_{datetime.now().timestamp()}",
            "timestamp_open": datetime.now().isoformat(),
            "features": features,
            "signal": int(signal),
            "confidence": float(confidence),
            "market_state": market_state,
            "strategy": strategy,
            "status": "open",
            "trailing_params": trailing_params or {},
            "breakeven_params": breakeven_params or {},
            "lot_params": lot_params or {},
            "htf_bias": htf_bias
        }
        self.memory["trades"].append(trade_entry)
        self.save_memory()
        return trade_entry["id"]
    
    def update_trade_result(self, trade_id, result, profit, duration_minutes,
                           trailing_triggered=False, breakeven_triggered=False):
        for trade in self.memory["trades"]:
            if trade.get("id") == trade_id:
                trade["timestamp_close"] = datetime.now().isoformat()
                trade["result"] = result
                trade["profit"] = float(profit)
                trade["duration_minutes"] = duration_minutes
                trade["status"] = "closed"
                trade["trailing_triggered"] = trailing_triggered
                trade["breakeven_triggered"] = breakeven_triggered
                trade["correct_prediction"] = (
                    (trade["signal"] == 1 and result == "win") or
                    (trade["signal"] == -1 and result == "win")
                )
                self.save_memory()
                return True
        return False
    
    def get_recent_trades(self, limit=100):
        closed_trades = [t for t in self.memory["trades"] if t.get("status") == "closed"]
        return sorted(closed_trades, key=lambda x: x.get("timestamp_close", ""), reverse=True)[:limit]
    
    def get_all_trades_for_training(self, limit=1000, min_profit=10.0):
        """
        Obtiene solo operaciones RENTABLES para entrenamiento ML
        
        Args:
            limit: Número máximo de trades
            min_profit: Profit mínimo en dólares (default: 10.0)
        """
        closed_trades = [t for t in self.memory["trades"] 
                        if t.get("status") == "closed" 
                        and t.get("profit", 0) >= min_profit]
        
        return sorted(closed_trades, key=lambda x: x.get("timestamp_close", ""), reverse=True)[:limit]
    
    def get_winning_trades_count(self, min_profit=5.0):
        """
        🆕 Cuenta operaciones ganadoras con profit >= threshold
        
        Args:
            min_profit: Profit mínimo para considerar ganadora (default: 5.0)
        
        Returns:
            int: Número de operaciones ganadoras
        """
        closed_trades = [t for t in self.memory["trades"] 
                        if t.get("status") == "closed" 
                        and t.get("profit", 0) >= min_profit]
        
        return len(closed_trades)
    
    def get_performance_metrics(self):
        closed_trades = [t for t in self.memory["trades"] if t.get("status") == "closed"]
        
        if len(closed_trades) == 0:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "prediction_accuracy": 0,
                "total_profit": 0,
                "avg_profit_per_trade": 0
            }
        
        total_trades = len(closed_trades)
        winning_trades = sum(1 for t in closed_trades if t.get("result") == "win")
        correct_predictions = sum(1 for t in closed_trades if t.get("correct_prediction"))
        total_profit = sum(t.get("profit", 0) for t in closed_trades)
        
        return {
            "total_trades": total_trades,
            "win_rate": (winning_trades / total_trades) * 100 if total_trades > 0 else 0,
            "prediction_accuracy": (correct_predictions / total_trades) * 100 if total_trades > 0 else 0,
            "total_profit": total_profit,
            "avg_profit_per_trade": total_profit / total_trades if total_trades > 0 else 0
        }
    
    # 🆕 NUEVO: Método para obtener estadísticas por estrategia
    def get_strategy_statistics(self):
        """
        Obtiene estadísticas detalladas por estrategia
        
        Returns:
            dict: Diccionario con estadísticas por estrategia
        """
        closed_trades = [t for t in self.memory["trades"] if t.get("status") == "closed"]
        
        # Inicializar estadísticas
        stats = {
            'ml': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'sr': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'fibo': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'price_action': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'candlestick': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'liquidity': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0}
        }
        
        # Procesar cada operación cerrada
        for trade in closed_trades:
            strategy = trade.get("strategy", "unknown")
            
            # Solo procesar estrategias válidas
            if strategy not in stats:
                continue
            
            result = trade.get("result", "unknown")
            profit = trade.get("profit", 0.0)
            
            # Actualizar estadísticas
            stats[strategy]['operations'] += 1
            stats[strategy]['profit'] += profit
            
            if result == "win":
                stats[strategy]['wins'] += 1
            elif result == "loss":
                stats[strategy]['losses'] += 1
        
        return stats


class ProfitTracker:
    """Sistema para trackear profit por hora y por día"""
    
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.profit_file = os.path.join(data_dir, "profit_tracking.json")
        
        # 🆕 SOLUCIÓN: Crear carpeta si no existe
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        self.hourly_profit = {str(i): 0.0 for i in range(24)}
        self.daily_profit = {str(i): 0.0 for i in range(1, 32)}
        
        self.current_day = datetime.now().day
        self.current_hour = datetime.now().hour
        
        self.load_tracking()
    
    def load_tracking(self):
        if os.path.exists(self.profit_file):
            try:
                with open(self.profit_file, 'r') as f:
                    data = json.load(f)
                    self.hourly_profit = data.get('hourly_profit', self.hourly_profit)
                    self.daily_profit = data.get('daily_profit', self.daily_profit)
                    self.current_day = data.get('current_day', datetime.now().day)
            except:
                pass
    
    def save_tracking(self):
        try:
            data = {
                'hourly_profit': self.hourly_profit,
                'daily_profit': self.daily_profit,
                'current_day': self.current_day,
                'last_update': datetime.now().isoformat()
            }
            with open(self.profit_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error guardando tracking: {e}")
    
    def update_hourly_profit(self, profit_value):
        current_hour = datetime.now().hour
        self.hourly_profit[str(current_hour)] = profit_value
        self.save_tracking()
    
    def update_daily_profit(self, profit_value):
        current_day = datetime.now().day
        self.daily_profit[str(current_day)] = profit_value
        self.current_day = current_day
        self.save_tracking()
    
    def reset_if_new_day(self):
        current_day = datetime.now().day
        if current_day != self.current_day:
            self.hourly_profit = {str(i): 0.0 for i in range(24)}
            self.current_day = current_day
            self.save_tracking()
    
    def get_hourly_data(self):
        hours = list(range(24))
        profits = [self.hourly_profit.get(str(h), 0.0) for h in hours]
        return hours, profits
    
    def get_daily_data(self):
        days = list(range(1, 32))
        profits = [self.daily_profit.get(str(d), 0.0) for d in days]
        return days, profits
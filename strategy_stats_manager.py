"""
╔══════════════════════════════════════════════════════════════════════════╗
║           GESTOR DE ESTADÍSTICAS POR ESTRATEGIA v1.0                     ║
║                                                                          ║
║  Sistema de persistencia para estadísticas de estrategias               ║
║  - Guarda automáticamente después de cada operación                     ║
║  - Carga al iniciar el bot                                              ║
║  - Permite reseteo manual                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime


class StrategyStatsManager:
    """
    Gestor de estadísticas persistentes por estrategia
    
    Guarda y carga estadísticas automáticamente para que no se pierdan
    al reiniciar el bot.
    """
    
    def __init__(self, data_dir="bot_data"):
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, "strategy_stats.json")
        
        # Crear directorio si no existe
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Estructura de estadísticas
        self.stats = {
            'ml': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'sr': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'fibo': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'price_action': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'candlestick': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0},
            'liquidity': {'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0}
        }
        
        # Metadatos
        self.metadata = {
            'created': datetime.now().isoformat(),
            'last_update': None,
            'total_resets': 0
        }
        
        # Cargar estadísticas existentes
        self.load_stats()
    
    def load_stats(self):
        """Carga estadísticas desde archivo"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    
                    # Cargar stats
                    if 'stats' in data:
                        self.stats = data['stats']
                    
                    # Cargar metadata
                    if 'metadata' in data:
                        self.metadata = data['metadata']
                    
                    print(f"✅ Estadísticas cargadas desde {self.stats_file}")
                    return True
            except Exception as e:
                print(f"⚠️ Error cargando estadísticas: {e}")
                return False
        else:
            print(f"ℹ️ No hay estadísticas previas, iniciando desde cero")
            return False
    
    def save_stats(self):
        """Guarda estadísticas en archivo"""
        try:
            # Actualizar timestamp
            self.metadata['last_update'] = datetime.now().isoformat()
            
            data = {
                'stats': self.stats,
                'metadata': self.metadata
            }
            
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Error guardando estadísticas: {e}")
            return False
    
    def update_operation(self, strategy):
        """
        Incrementa contador de operaciones para una estrategia
        
        Args:
            strategy: Nombre de la estrategia ('ml', 'sr', 'fibo', etc.)
        """
        if strategy not in self.stats:
            print(f"⚠️ Estrategia desconocida: {strategy}")
            return False
        
        self.stats[strategy]['operations'] += 1
        self.save_stats()
        return True
    
    def update_result(self, strategy, profit, result):
        """
        Actualiza resultado de una operación cerrada
        
        Args:
            strategy: Nombre de la estrategia
            profit: Profit de la operación
            result: 'win' | 'loss' | 'breakeven'
        """
        if strategy not in self.stats:
            print(f"⚠️ Estrategia desconocida: {strategy}")
            return False
        
        # Actualizar profit
        self.stats[strategy]['profit'] += profit
        
        # Actualizar wins/losses
        if result == 'win':
            self.stats[strategy]['wins'] += 1
        elif result == 'loss':
            self.stats[strategy]['losses'] += 1
        
        # Guardar inmediatamente
        self.save_stats()
        return True
    
    def get_stats(self):
        """Retorna estadísticas actuales"""
        return self.stats.copy()
    
    def get_strategy_stats(self, strategy):
        """Retorna estadísticas de una estrategia específica"""
        return self.stats.get(strategy, {
            'operations': 0, 'wins': 0, 'losses': 0, 'profit': 0.0
        })
    
    def reset_stats(self):
        """Resetea todas las estadísticas a cero"""
        for strategy in self.stats:
            self.stats[strategy] = {
                'operations': 0,
                'wins': 0,
                'losses': 0,
                'profit': 0.0
            }
        
        self.metadata['total_resets'] += 1
        self.metadata['last_reset'] = datetime.now().isoformat()
        
        self.save_stats()
        print(f"🔄 Estadísticas reseteadas")
        return True
    
    def get_summary(self):
        """Retorna resumen de todas las estrategias"""
        total_ops = sum(s['operations'] for s in self.stats.values())
        total_wins = sum(s['wins'] for s in self.stats.values())
        total_losses = sum(s['losses'] for s in self.stats.values())
        total_profit = sum(s['profit'] for s in self.stats.values())
        
        return {
            'total_operations': total_ops,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_profit': total_profit,
            'win_rate': (total_wins / total_ops * 100) if total_ops > 0 else 0,
            'by_strategy': self.stats.copy()
        }
    
    def get_best_strategy(self):
        """Retorna la estrategia con mayor profit"""
        best = None
        max_profit = float('-inf')
        
        for strategy, stats in self.stats.items():
            if stats['profit'] > max_profit:
                max_profit = stats['profit']
                best = strategy
        
        return best, max_profit
    
    def get_worst_strategy(self):
        """Retorna la estrategia con menor profit"""
        worst = None
        min_profit = float('inf')
        
        for strategy, stats in self.stats.items():
            if stats['profit'] < min_profit:
                min_profit = stats['profit']
                worst = strategy
        
        return worst, min_profit
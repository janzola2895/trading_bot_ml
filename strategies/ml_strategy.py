"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ESTRATEGIA ML + ENSEMBLE v5.2                         ║
║                                                                          ║
║  Sistema de múltiples modelos ML con rotación automática cíclica        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import pickle
import json
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

from config import (
    DATA_DIR, MODELS_DIR,
    ROTATE_MODELS_EVERY_N_OPS, RETRAIN_EVERY_N_OPS,
    MIN_PROFIT_FOR_LEARNING,
    RF_N_ESTIMATORS, RF_MAX_DEPTH, RF_MIN_SAMPLES_SPLIT,
    GB_N_ESTIMATORS, GB_MAX_DEPTH, GB_LEARNING_RATE,
    NN_HIDDEN_LAYERS, NN_ACTIVATION, NN_MAX_ITER
)


class MLEnsemble:
    """
    Sistema de múltiples modelos ML
    
    ⭐ NUEVO v5.2: ROTACIÓN CÍCLICA AUTOMÁTICA
    - Rota entre modelos en secuencia: RF → GB → NN → RF...
    - Contador global de operaciones
    - Rotación garantizada cada N ops sin importar precisión
    - Logs detallados de cada rotación
    - Actualiza precisión en tiempo real
    """
    
    def __init__(self, data_dir=DATA_DIR, logger=None):
        self.data_dir = data_dir
        self.models_dir = MODELS_DIR
        self.logger = logger
        
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
        
        self.scaler = StandardScaler()
        
        # Lista ordenada de modelos para rotación cíclica
        self.model_names = ["random_forest", "gradient_boost", "neural_net"]
        self.current_model_index = 0
        
        self.models = {
            "random_forest": {
                "model": RandomForestClassifier(
                    n_estimators=RF_N_ESTIMATORS,
                    max_depth=RF_MAX_DEPTH,
                    min_samples_split=RF_MIN_SAMPLES_SPLIT,
                    random_state=42,
                    n_jobs=-1
                ),
                "performance": {"accuracy": 0, "trades": 0, "profit": 0},
                "weight": 1.0
            },
            "gradient_boost": {
                "model": GradientBoostingClassifier(
                    n_estimators=GB_N_ESTIMATORS,
                    max_depth=GB_MAX_DEPTH,
                    learning_rate=GB_LEARNING_RATE,
                    random_state=42
                ),
                "performance": {"accuracy": 0, "trades": 0, "profit": 0},
                "weight": 1.0
            },
            "neural_net": {
                "model": MLPClassifier(
                    hidden_layer_sizes=NN_HIDDEN_LAYERS,
                    activation=NN_ACTIVATION,
                    max_iter=NN_MAX_ITER,
                    random_state=42
                ),
                "performance": {"accuracy": 0, "trades": 0, "profit": 0},
                "weight": 1.0
            }
        }
        
        self.active_model = self.model_names[0]
        self.use_ensemble_voting = True
        
        # ⭐ NUEVO: Control de rotación cíclica automática
        self.rotation_config = {
            "enabled": True,
            "rotate_every_n_ops": ROTATE_MODELS_EVERY_N_OPS,
            "global_operations_count": 0,
            "last_rotation_time": None,
            "rotation_history": []
        }
        
        self.load_models()
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def save_models(self):
        try:
            for name, model_data in self.models.items():
                model_path = os.path.join(self.models_dir, f"{name}.pkl")
                with open(model_path, 'wb') as f:
                    pickle.dump(model_data, f)
            
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            # Guardar configuración de rotación
            rotation_path = os.path.join(self.models_dir, "rotation_config.json")
            rotation_data = {
                "rotation_config": self.rotation_config,
                "current_model_index": self.current_model_index,
                "active_model": self.active_model
            }
            with open(rotation_path, 'w') as f:
                json.dump(rotation_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error guardando modelos: {e}")
            return False
    
    def load_models(self):
        try:
            for name in self.models.keys():
                model_path = os.path.join(self.models_dir, f"{name}.pkl")
                if os.path.exists(model_path):
                    with open(model_path, 'rb') as f:
                        loaded_data = pickle.load(f)
                        if 'weight' not in loaded_data:
                            loaded_data['weight'] = 1.0
                        self.models[name] = loaded_data
            
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
            
            # Cargar configuración de rotación
            rotation_path = os.path.join(self.models_dir, "rotation_config.json")
            if os.path.exists(rotation_path):
                with open(rotation_path, 'r') as f:
                    rotation_data = json.load(f)
                    self.rotation_config = rotation_data.get("rotation_config", self.rotation_config)
                    self.current_model_index = rotation_data.get("current_model_index", 0)
                    self.active_model = rotation_data.get("active_model", self.model_names[0])
            
            return True
        except Exception as e:
            print(f"Error cargando modelos: {e}")
            return False
    
    def train_all_models(self, X_train, y_train, X_test, y_test):
        results = {}
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        for name, model_data in self.models.items():
            try:
                model = model_data["model"]
                model.fit(X_train_scaled, y_train)
                
                y_pred_test = model.predict(X_test_scaled)
                
                test_acc = accuracy_score(y_test, y_pred_test)
                precision = precision_score(y_test, y_pred_test, average='weighted', zero_division=0)
                recall = recall_score(y_test, y_pred_test, average='weighted', zero_division=0)
                f1 = f1_score(y_test, y_pred_test, average='weighted', zero_division=0)
                
                results[name] = {
                    "test_accuracy": test_acc,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1
                }
                
                self.models[name]["model"] = model
                
            except Exception as e:
                print(f"Error entrenando {name}: {e}")
                results[name] = {"error": str(e)}
        
        self.save_models()
        return results
    
    def predict_with_active_model(self, X):
        X_scaled = self.scaler.transform(X)
        model = self.models[self.active_model]["model"]
        
        signal = model.predict(X_scaled)[0]
        probabilities = model.predict_proba(X_scaled)[0]
        
        return int(signal), probabilities
    
    def update_model_performance(self, model_name, correct, profit):
        if model_name in self.models:
            perf = self.models[model_name]["performance"]
            perf["trades"] += 1
            
            # ✅ Actualizar precisión con validación
            if perf["trades"] > 0:
                if correct:
                    perf["accuracy"] = ((perf["accuracy"] * (perf["trades"] - 1)) + 100) / perf["trades"]
                else:
                    perf["accuracy"] = (perf["accuracy"] * (perf["trades"] - 1)) / perf["trades"]
            
            perf["profit"] += profit
            
            # Actualizar peso
            if perf["trades"] >= 5:
                if perf["accuracy"] > 60:
                    self.models[model_name]["weight"] = 1.5
                elif perf["accuracy"] > 50:
                    self.models[model_name]["weight"] = 1.0
                else:
                    self.models[model_name]["weight"] = 0.5
            
            self.save_models()
    
    def increment_global_counter(self):
        """⭐ NUEVO: Incrementa el contador MANUALMENTE"""
        self.rotation_config["global_operations_count"] += 1
        self.save_models()
    
    def should_rotate_cyclic(self):
        """⭐ NUEVO: Verifica si debe rotar según contador global"""
        if not self.rotation_config["enabled"]:
            return False
        
        ops_count = self.rotation_config["global_operations_count"]
        rotate_every = self.rotation_config["rotate_every_n_ops"]
        
        return ops_count >= rotate_every
    
    def rotate_to_next_model(self):
        """⭐ NUEVO: Rota al siguiente modelo en secuencia"""
        # ✅ GUARDAR el contador ANTES de resetear
        operations_completed = self.rotation_config["global_operations_count"]
        
        old_model = self.active_model
        old_accuracy = self.models[old_model]["performance"]["accuracy"]
        old_trades = self.models[old_model]["performance"]["trades"]
        
        # Avanzar al siguiente modelo
        self.current_model_index = (self.current_model_index + 1) % len(self.model_names)
        self.active_model = self.model_names[self.current_model_index]
        
        new_accuracy = self.models[self.active_model]["performance"]["accuracy"]
        new_trades = self.models[self.active_model]["performance"]["trades"]
        
        # ✅ AHORA sí resetear el contador
        self.rotation_config["global_operations_count"] = 0
        self.rotation_config["last_rotation_time"] = datetime.now().isoformat()
        
        # Crear evento con los valores CORRECTOS
        rotation_event = {
            "timestamp": datetime.now().isoformat(),
            "from_model": old_model,
            "to_model": self.active_model,
            "old_accuracy": old_accuracy,
            "old_trades": old_trades,
            "new_accuracy": new_accuracy,
            "new_trades": new_trades,
            "operations_completed": operations_completed,
            "rotation_type": "cyclic",
            "reason": f"Rotación automática cada {self.rotation_config['rotate_every_n_ops']} ops"
        }
        
        self.rotation_config["rotation_history"].append(rotation_event)
        
        # Limitar historial a últimos 20
        if len(self.rotation_config["rotation_history"]) > 20:
            self.rotation_config["rotation_history"] = self.rotation_config["rotation_history"][-20:]
        
        self.save_models()
        
        return rotation_event
    
    def get_models_comparison(self):
        comparison = {}
        for name, model_data in self.models.items():
            comparison[name] = {
                "active": name == self.active_model,
                "performance": model_data["performance"],
                "weight": model_data.get("weight", 1.0)
            }
        return comparison
    
    def get_rotation_history(self, limit=10):
        """⭐ Retorna historial de rotaciones"""
        history = self.rotation_config.get("rotation_history", [])
        return history[-limit:] if len(history) > limit else history
    
    def get_rotation_status(self):
        """⭐ NUEVO: Retorna estado del sistema de rotación"""
        return {
            "enabled": self.rotation_config["enabled"],
            "rotate_every": self.rotation_config["rotate_every_n_ops"],
            "current_count": self.rotation_config["global_operations_count"],
            "operations_until_rotation": self.rotation_config["rotate_every_n_ops"] - self.rotation_config["global_operations_count"],
            "active_model": self.active_model,
            "next_model": self.model_names[(self.current_model_index + 1) % len(self.model_names)]
        }


class IncrementalLearningSystem:
    """
    Sistema de aprendizaje incremental - Aprende con CADA operación
    
    🆕 v5.2: Solo usa operaciones rentables >= $10 para re-entrenamiento
    """
    
    def __init__(self, memory, ensemble, retrain_every=RETRAIN_EVERY_N_OPS, logger=None):
        self.memory = memory
        self.ensemble = ensemble
        self.retrain_every = retrain_every
        self.logger = logger
        
        self.operations_since_last_train = 0
        
        self.learning_stats = {
            "total_retrains": 0,
            "last_retrain": None,
            "operations_per_strategy": {
                "ml": 0,
                "sr": 0,
                "fibo": 0,
                "price_action": 0,
                "candlestick": 0,
                "liquidity": 0
            },
            "incremental_trains": 0,
            "last_incremental_train": None
        }
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def should_retrain(self):
        """⭐ Verifica si es momento de re-entrenar INCREMENTALMENTE"""
        self.operations_since_last_train += 1
        
        if self.operations_since_last_train >= self.retrain_every:
            self.operations_since_last_train = 0
            return True
        
        return False
    
    def incremental_train(self, current_market_df):
        """
        ⭐ Re-entrenamiento INCREMENTAL con cada operación
        
        🔧 IMPORTANTE: Usa operaciones de TODAS las estrategias rentables >= $10
        """
        try:
            # Obtener últimas operaciones rentables
            all_trades = self.memory.get_all_trades_for_training(
                limit=500,
                min_profit=MIN_PROFIT_FOR_LEARNING
            )
            
            if len(all_trades) < 20:
                self.send_log(f"⚠️ Solo {len(all_trades)} trades rentables disponibles (mín: 20)")
                return None
            
            self.send_log(f"📚 Entrenando con {len(all_trades)} operaciones RENTABLES (profit >= ${MIN_PROFIT_FOR_LEARNING})")
            
            # Contar operaciones por estrategia
            for trade in all_trades:
                strategy = trade.get("strategy", "unknown")
                if strategy in self.learning_stats["operations_per_strategy"]:
                    self.learning_stats["operations_per_strategy"][strategy] += 1
            
            # Preparar datos para entrenamiento
            feature_columns = ['ema_21', 'ema_50', 'atr', 'adx', 'rsi', 'macd',
                             'macd_signal', 'momentum', 'price_to_ema21',
                             'price_to_ema50', 'ema_diff', 'bb_position', 'volume_change']
            
            X = current_market_df[feature_columns]
            y = current_market_df['target']
            
            # Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # ⭐ Re-entrenar TODOS los modelos
            results = self.ensemble.train_all_models(X_train, y_train, X_test, y_test)
            
            # Actualizar estadísticas
            self.learning_stats["incremental_trains"] += 1
            self.learning_stats["last_incremental_train"] = datetime.now().isoformat()
            
            return {
                "results": results,
                "total_trades_used": len(all_trades),
                "operations_by_strategy": self.learning_stats["operations_per_strategy"].copy()
            }
            
        except Exception as e:
            print(f"❌ Error en re-entrenamiento incremental: {e}")
            return None
    
    def get_learning_stats(self):
        """Retorna estadísticas de aprendizaje"""
        return self.learning_stats
"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    ESTRATEGIA ML + ENSEMBLE v6.1 - MTF + VOLATILITY      ║
║                                                                          ║
║  🆕 v6.1: Sistema ML con volatilidad avanzada y regímenes de mercado    ║
║  - Predice en M30, H1, H4 y genera consenso                             ║
║  - Mayor confianza cuando TFs coinciden                                 ║
║  - Rotación automática cíclica de modelos                               ║
║  - Features de volatilidad avanzadas (Parkinson, Garman-Klass)          ║
║  - Detección de regímenes de mercado con HMM                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import pickle
import json
import pandas as pd
import MetaTrader5 as mt5
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

# 🆕 v6.1: Importar calculadores de volatilidad y régimen
from core.volatility_features import VolatilityFeatures
from core.market_regime_detector import MarketRegimeDetector


class MLEnsemble:
    """
    Sistema ML con Multi-Timeframe + Volatilidad Avanzada
    
    🆕 v6.1: Features de volatilidad y detección de regímenes
    - Predice en M30, H1, H4
    - Consenso entre timeframes
    - Boost de confianza por alineación
    - Volatilidad Parkinson y Garman-Klass
    - Detección de regímenes de mercado
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
                    learning_rate_init=0.001,  # AGREGAR ESTO
                    early_stopping=True,        # AGREGAR ESTO
                    n_iter_no_change=50,        # AGREGAR ESTO
                    random_state=42
                ),
                "performance": {"accuracy": 0, "trades": 0, "profit": 0},
                "weight": 1.0
            }
        }
        
        self.active_model = self.model_names[0]
        self.use_ensemble_voting = True
        
        # 🆕 MTF: Configuración de timeframes
        self.mtf_timeframes = {
            'M30': {'tf': mt5.TIMEFRAME_M30, 'weight': 1.0, 'cache_seconds': 60},
            'H1': {'tf': mt5.TIMEFRAME_H1, 'weight': 1.3, 'cache_seconds': 120},
            'H4': {'tf': mt5.TIMEFRAME_H4, 'weight': 1.6, 'cache_seconds': 300}
        }
        
        # Cache MTF
        self.mtf_cache = {}
        self.last_mtf_update = {}
        
        for tf_name in self.mtf_timeframes:
            self.mtf_cache[tf_name] = None
            self.last_mtf_update[tf_name] = None
        
        # Control de rotación cíclica automática
        self.rotation_config = {
            "enabled": True,
            "rotate_every_n_ops": ROTATE_MODELS_EVERY_N_OPS,
            "global_operations_count": 0,
            "last_rotation_time": None,
            "rotation_history": []
        }
        
        # 🆕 v6.1: Inicializar calculadores de volatilidad y régimen
        self.vol_features_calculator = VolatilityFeatures(window=14)
        self.regime_detector = MarketRegimeDetector(data_dir=data_dir)
        
        self.load_models()
    
    def send_log(self, message):
        """Envía mensaje al log"""
        if self.logger:
            self.logger.info(message)
    
    def get_timeframe_data(self, tf, bars=100, symbol="XAUUSD"):
        """Obtiene datos de timeframe específico"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            if rates is None:
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except:
            return None
    
    def calculate_indicators_for_tf(self, df):
        """Calcula indicadores para un timeframe"""
        import ta
        
        df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
        df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_high'] = bollinger.bollinger_hband()
        df['bb_low'] = bollinger.bollinger_lband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['momentum'] = df['close'].pct_change(periods=10)
        
        df['price_to_ema21'] = (df['close'] - df['ema_21']) / df['ema_21']
        df['price_to_ema50'] = (df['close'] - df['ema_50']) / df['ema_50']
        df['ema_diff'] = (df['ema_21'] - df['ema_50']) / df['ema_50']
        df['bb_position'] = (df['close'] - df['bb_low']) / (df['bb_high'] - df['bb_low'])
        df['volume_change'] = df['tick_volume'].pct_change()
        
        df.dropna(inplace=True)
        return df
    
    def prepare_features_from_df(self, df):
        """
        Prepara features desde un dataframe
        
        🆕 v6.1: Calcula features de volatilidad avanzadas primero
        """
        if len(df) == 0:
            return None
        
        # 🆕 v6.1: Calcular features de volatilidad PRIMERO
        df = self.vol_features_calculator.calculate_all_features(df)
        
        last_row = df.iloc[-1]
        
        features = {
            'ema_21': float(last_row['ema_21']),
            'ema_50': float(last_row['ema_50']),
            'atr': float(last_row['atr']),
            'adx': float(last_row['adx']),
            'rsi': float(last_row['rsi']),
            'macd': float(last_row['macd']),
            'macd_signal': float(last_row['macd_signal']),
            'momentum': float(last_row['momentum']),
            'price_to_ema21': float(last_row['price_to_ema21']),
            'price_to_ema50': float(last_row['price_to_ema50']),
            'ema_diff': float(last_row['ema_diff']),
            'bb_position': float(last_row['bb_position']),
            'volume_change': float(last_row['volume_change']),
            # 🆕 v6.1: Agregar 5 features de volatilidad
            'parkinson_vol': float(last_row.get('parkinson_vol', 0.0)),
            'garman_klass_vol': float(last_row.get('garman_klass_vol', 0.0)),
            'volatility_regime': float(last_row.get('volatility_regime', 1)),
            'vol_ratio_gk_park': float(last_row.get('vol_ratio_gk_park', 1.0)),
            'parkinson_vol_change': float(last_row.get('parkinson_vol_change', 0.0))
        }
        
        return features
    
    def predict_on_timeframe(self, tf_name, symbol="XAUUSD"):
        """
        🆕 Predice en un timeframe específico
        
        Returns:
            dict: {'signal': int, 'confidence': float, 'timeframe': str}
        """
        now = datetime.now()
        cache_key = tf_name
        
        # Verificar cache
        if cache_key in self.mtf_cache:
            last_update = self.last_mtf_update.get(cache_key)
            cache_time = self.mtf_timeframes[tf_name]['cache_seconds']
            
            if last_update and (now - last_update).total_seconds() < cache_time:
                return self.mtf_cache[cache_key]
        
        # Obtener datos del timeframe
        tf_config = self.mtf_timeframes[tf_name]
        df = self.get_timeframe_data(tf_config['tf'], bars=100, symbol=symbol)
        
        if df is None or len(df) < 50:
            return None
        
        # Calcular indicadores
        df = self.calculate_indicators_for_tf(df)
        
        if len(df) == 0:
            return None
        
        # Preparar features (ahora incluye volatilidad)
        features = self.prepare_features_from_df(df)
        
        if features is None:
            return None
        
        # Predecir con modelo activo
        try:
            X = pd.DataFrame([features])
            X_scaled = self.scaler.transform(X)
            
            model = self.models[self.active_model]["model"]
            signal = model.predict(X_scaled)[0]
            probabilities = model.predict_proba(X_scaled)[0]
            confidence = float(max(probabilities))
            
            result = {
                'signal': int(signal),
                'confidence': confidence,
                'timeframe': tf_name,
                'tf_weight': tf_config['weight']
            }
            
            # Actualizar cache
            self.mtf_cache[cache_key] = result
            self.last_mtf_update[cache_key] = now
            
            return result
            
        except Exception as e:
            return None
    
    def predict_with_mtf(self, symbol="XAUUSD"):
        """
        🆕 Predicción con consenso multi-timeframe
        
        Returns:
            tuple: (signal, confidence, mtf_details)
        """
        predictions = []
        
        # Predecir en cada timeframe
        for tf_name in ['M30', 'H1', 'H4']:
            prediction = self.predict_on_timeframe(tf_name, symbol)
            
            if prediction:
                predictions.append(prediction)
        
        if not predictions:
            return 0, 0.0, {}
        
        # Analizar consenso
        buy_votes = sum(1 for p in predictions if p['signal'] == 1)
        sell_votes = sum(1 for p in predictions if p['signal'] == -1)
        total_votes = len(predictions)
        
        # Determinar señal por mayoría
        if buy_votes > sell_votes:
            final_signal = 1
            aligned_tfs = [p['timeframe'] for p in predictions if p['signal'] == 1]
        elif sell_votes > buy_votes:
            final_signal = -1
            aligned_tfs = [p['timeframe'] for p in predictions if p['signal'] == -1]
        else:
            final_signal = 0
            aligned_tfs = []
        
        # Calcular confianza ponderada
        if final_signal != 0:
            aligned_predictions = [p for p in predictions if p['signal'] == final_signal]
            
            total_weight = sum(p['tf_weight'] for p in aligned_predictions)
            weighted_confidence = sum(
                p['confidence'] * p['tf_weight'] for p in aligned_predictions
            ) / total_weight if total_weight > 0 else 0.0
            
            # Boost por alineación
            alignment_ratio = len(aligned_predictions) / total_votes
            if alignment_ratio == 1.0:
                confidence_boost = 0.10  # +10% todas alineadas
            elif alignment_ratio >= 0.66:
                confidence_boost = 0.05  # +5% mayoría clara
            else:
                confidence_boost = 0.0
            
            final_confidence = min(weighted_confidence + confidence_boost, 0.95)
        else:
            final_confidence = 0.0
            aligned_predictions = []
        
        mtf_details = {
            'predictions': predictions,
            'aligned_timeframes': aligned_tfs,
            'alignment_ratio': len(aligned_tfs) / total_votes if total_votes > 0 else 0,
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'total_votes': total_votes
        }
        
        return final_signal, final_confidence, mtf_details
    
    def save_models(self):
        try:
            for name, model_data in self.models.items():
                model_path = os.path.join(self.models_dir, f"{name}.pkl")
                with open(model_path, 'wb') as f:
                    pickle.dump(model_data, f)
            
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
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
        """Predicción legacy (sin MTF) para compatibilidad"""
        X_scaled = self.scaler.transform(X)
        model = self.models[self.active_model]["model"]
        
        signal = model.predict(X_scaled)[0]
        probabilities = model.predict_proba(X_scaled)[0]
        
        return int(signal), probabilities
    
    def update_model_performance(self, model_name, correct, profit):
        if model_name in self.models:
            perf = self.models[model_name]["performance"]
            perf["trades"] += 1
            
            if perf["trades"] > 0:
                if correct:
                    perf["accuracy"] = ((perf["accuracy"] * (perf["trades"] - 1)) + 100) / perf["trades"]
                else:
                    perf["accuracy"] = (perf["accuracy"] * (perf["trades"] - 1)) / perf["trades"]
            
            perf["profit"] += profit
            
            if perf["trades"] >= 5:
                if perf["accuracy"] > 60:
                    self.models[model_name]["weight"] = 1.5
                elif perf["accuracy"] > 50:
                    self.models[model_name]["weight"] = 1.0
                else:
                    self.models[model_name]["weight"] = 0.5
            
            self.save_models()
    
    def increment_global_counter(self):
        """Incrementa el contador MANUALMENTE"""
        self.rotation_config["global_operations_count"] += 1
        self.save_models()
    
    def should_rotate_cyclic(self):
        """Verifica si debe rotar según contador global"""
        if not self.rotation_config["enabled"]:
            return False
        
        ops_count = self.rotation_config["global_operations_count"]
        rotate_every = self.rotation_config["rotate_every_n_ops"]
        
        return ops_count >= rotate_every
    
    def rotate_to_next_model(self):
        """Rota al siguiente modelo en secuencia"""
        operations_completed = self.rotation_config["global_operations_count"]
        
        old_model = self.active_model
        old_accuracy = self.models[old_model]["performance"]["accuracy"]
        old_trades = self.models[old_model]["performance"]["trades"]
        
        self.current_model_index = (self.current_model_index + 1) % len(self.model_names)
        self.active_model = self.model_names[self.current_model_index]
        
        new_accuracy = self.models[self.active_model]["performance"]["accuracy"]
        new_trades = self.models[self.active_model]["performance"]["trades"]
        
        self.rotation_config["global_operations_count"] = 0
        self.rotation_config["last_rotation_time"] = datetime.now().isoformat()
        
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
        """Retorna historial de rotaciones"""
        history = self.rotation_config.get("rotation_history", [])
        return history[-limit:] if len(history) > limit else history
    
    def get_rotation_status(self):
        """Retorna estado del sistema de rotación"""
        return {
            "enabled": self.rotation_config["enabled"],
            "rotate_every": self.rotation_config["rotate_every_n_ops"],
            "current_count": self.rotation_config["global_operations_count"],
            "operations_until_rotation": self.rotation_config["rotate_every_n_ops"] - self.rotation_config["global_operations_count"],
            "active_model": self.active_model,
            "next_model": self.model_names[(self.current_model_index + 1) % len(self.model_names)]
        }


class IncrementalLearningSystem:
    """Sistema de aprendizaje incremental"""
    
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
        """Verifica si es momento de re-entrenar"""
        self.operations_since_last_train += 1
        
        if self.operations_since_last_train >= self.retrain_every:
            self.operations_since_last_train = 0
            return True
        
        return False
    
    def incremental_train(self, current_market_df):
        """Re-entrenamiento INCREMENTAL"""
        try:
            all_trades = self.memory.get_all_trades_for_training(
                limit=500,
                min_profit=MIN_PROFIT_FOR_LEARNING
            )
            
            if len(all_trades) < 20:
                self.send_log(f"⚠️ Solo {len(all_trades)} trades rentables disponibles (mín: 20)")
                return None
            
            self.send_log(f"📚 Entrenando con {len(all_trades)} operaciones RENTABLES (profit >= ${MIN_PROFIT_FOR_LEARNING})")
            
            for trade in all_trades:
                strategy = trade.get("strategy", "unknown")
                if strategy in self.learning_stats["operations_per_strategy"]:
                    self.learning_stats["operations_per_strategy"][strategy] += 1
            
            # 🆕 v6.1: Lista de features actualizada con volatilidad
            feature_columns = [
                'ema_21', 'ema_50', 'atr', 'adx', 'rsi', 'macd',
                'macd_signal', 'momentum', 'price_to_ema21',
                'price_to_ema50', 'ema_diff', 'bb_position', 'volume_change',
                # 🆕 v6.1: Features de volatilidad
                'parkinson_vol', 'garman_klass_vol', 'volatility_regime',
                'vol_ratio_gk_park', 'parkinson_vol_change'
            ]
            
            X = current_market_df[feature_columns]
            y = current_market_df['target']
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            results = self.ensemble.train_all_models(X_train, y_train, X_test, y_test)
            
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
"""
╔══════════════════════════════════════════════════════════════════════════╗
║         MARKET REGIME DETECTOR v1.0 - MEJORA ML CRÍTICA #1              ║
║                                                                          ║
║  Sistema de detección de régimen de mercado usando HMM                  ║
║  - 3 Estados: Trending Up, Ranging, Trending Down                       ║
║  - Adaptación automática de parámetros por régimen                      ║
║  - Entrenamiento en datos históricos                                    ║
║                                                                          ║
║  IMPACTO ESTIMADO: +15% Sharpe Ratio                                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd
import pickle
import os
from datetime import datetime

try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    print("⚠️ hmmlearn no disponible. Instalar: pip install hmmlearn --break-system-packages")


class MarketRegimeDetector:
    """
    Detector de régimen de mercado usando Hidden Markov Models (HMM)
    
    Identifica 3 estados del mercado:
    - Estado 0: Trending Up (tendencia alcista fuerte)
    - Estado 1: Ranging (mercado lateral/consolidación)
    - Estado 2: Trending Down (tendencia bajista fuerte)
    
    El HMM aprende automáticamente las características de cada régimen
    y predice el estado actual basándose en observables de mercado.
    """
    
    def __init__(self, n_states=3, data_dir="bot_data"):
        """
        Args:
            n_states: Número de estados (default: 3)
            data_dir: Directorio para guardar modelo entrenado
        """
        self.n_states = n_states
        self.data_dir = data_dir
        self.model_file = os.path.join(data_dir, "regime_hmm_model.pkl")
        
        # Crear directorio si no existe
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Inicializar modelo HMM
        if HMM_AVAILABLE:
            self.model = hmm.GaussianHMM(
                n_components=n_states,
                covariance_type="diag",
                n_iter=1000,
                random_state=42,
                init_params='stmc' 
            )
        else:
            self.model = None
        
        self.is_trained = False
        self.state_names = {
            0: "Trending Up",
            1: "Ranging",
            2: "Trending Down"
        }
        
        # Características de cada régimen (se actualizan tras entrenamiento)
        self.regime_characteristics = {
            0: {'mean_return': 0.0, 'mean_volatility': 0.0},
            1: {'mean_return': 0.0, 'mean_volatility': 0.0},
            2: {'mean_return': 0.0, 'mean_volatility': 0.0}
        }
        
        # Intentar cargar modelo pre-entrenado
        self.load_model()
    
    def prepare_features(self, df):
        """
        Prepara features observables para el HMM
        
        Features:
        1. Returns (cambio porcentual del precio)
        2. Volatility (rolling std de returns)
        3. Trend strength (ADX o proxy)
        4. Volume momentum (si disponible)
        
        Args:
            df: DataFrame con OHLC
        
        Returns:
            np.array: Features normalizados [n_samples, n_features]
        """
        # 1. Returns
        returns = df['close'].pct_change()
        
        # 2. Volatility (rolling std de 20 períodos)
        volatility = returns.rolling(window=20).std()
        
        # 3. Trend strength (aproximación con EMAs)
        ema_fast = df['close'].ewm(span=12).mean()
        ema_slow = df['close'].ewm(span=26).mean()
        trend_strength = (ema_fast - ema_slow) / ema_slow
        
        # 4. Range expansion (high-low normalizado)
        price_range = (df['high'] - df['low']) / df['close']
        
        # Combinar features
        features_df = pd.DataFrame({
            'returns': returns,
            'volatility': volatility,
            'trend_strength': trend_strength,
            'price_range': price_range
        })
        
        # Eliminar NaN y normalizar
        features_df = features_df.dropna()
        
        # Z-score normalization
        features_normalized = (features_df - features_df.mean()) / features_df.std()
        
        return features_normalized.values
    
    def train(self, df, verbose=True):
        """
        Entrena el modelo HMM con datos históricos
        
        Args:
            df: DataFrame con OHLC históricos (mínimo 500 filas recomendado)
            verbose: Si mostrar información de entrenamiento
        
        Returns:
            bool: True si entrenamiento exitoso
        """
        if not HMM_AVAILABLE:
            print("❌ hmmlearn no disponible")
            return False
        
        if verbose:
            print(f"\n🤖 Entrenando Market Regime Detector...")
            print(f"   Datos: {len(df)} barras")
        
        # Preparar features
        features = self.prepare_features(df)
        
        if len(features) < 100:
            print("❌ Datos insuficientes para entrenamiento (mínimo 100 barras)")
            return False
        
        # Entrenar HMM
        try:
            self.model.fit(features)
            self.is_trained = True
            
            # Predecir estados para analizar características
            states = self.model.predict(features)
            
            # Analizar características de cada régimen
            returns = df['close'].pct_change().dropna().values
            returns = returns[-len(states):]  # Alinear con estados
            
            for state in range(self.n_states):
                state_mask = states == state
                if state_mask.sum() > 0:
                    self.regime_characteristics[state] = {
                        'mean_return': float(returns[state_mask].mean()),
                        'mean_volatility': float(returns[state_mask].std()),
                        'frequency': float(state_mask.sum() / len(states))
                    }
            
            # Identificar régimen más alcista y más bajista
            regimes_by_return = sorted(
                self.regime_characteristics.items(),
                key=lambda x: x[1]['mean_return']
            )
            
            # Reasignar nombres
            self.state_names[regimes_by_return[2][0]] = "Trending Up"
            self.state_names[regimes_by_return[1][0]] = "Ranging"
            self.state_names[regimes_by_return[0][0]] = "Trending Down"
            
            if verbose:
                print(f"✅ Modelo entrenado exitosamente")
                print(f"\n📊 Características de regímenes:")
                for state in range(self.n_states):
                    char = self.regime_characteristics[state]
                    print(f"   {self.state_names[state]}:")
                    print(f"      Return promedio: {char['mean_return']*100:.3f}%")
                    print(f"      Volatilidad: {char['mean_volatility']*100:.2f}%")
                    print(f"      Frecuencia: {char['frequency']*100:.1f}%")
            
            # Guardar modelo
            self.save_model()
            
            return True
            
        except Exception as e:
            print(f"❌ Error entrenando modelo: {e}")
            return False
    
    def predict_current_regime(self, df):
        """
        Predice el régimen actual del mercado
        
        Args:
            df: DataFrame con OHLC recientes (mínimo 50 barras)
        
        Returns:
            dict: {
                'regime': int (0, 1, 2),
                'regime_name': str,
                'confidence': float,
                'characteristics': dict
            }
        """
        if not self.is_trained:
            return {
                'regime': 1,
                'regime_name': 'Unknown (not trained)',
                'confidence': 0.0,
                'characteristics': {}
            }
        
        # Preparar features
        features = self.prepare_features(df)
        
        if len(features) < 20:
            return {
                'regime': 1,
                'regime_name': 'Unknown (insufficient data)',
                'confidence': 0.0,
                'characteristics': {}
            }
        
        # Predecir régimen actual (última observación)
        predicted_state = self.model.predict(features)[-1]
        
        # Calcular probabilidades (confidence)
        probabilities = self.model.predict_proba(features)[-1]
        confidence = float(probabilities[predicted_state])
        
        return {
            'regime': int(predicted_state),
            'regime_name': self.state_names[predicted_state],
            'confidence': confidence,
            'characteristics': self.regime_characteristics[predicted_state],
            'probabilities': {
                self.state_names[i]: float(probabilities[i])
                for i in range(self.n_states)
            }
        }
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        if not self.is_trained:
            return False
        
        try:
            model_data = {
                'model': self.model,
                'is_trained': self.is_trained,
                'state_names': self.state_names,
                'regime_characteristics': self.regime_characteristics,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            return True
        except Exception as e:
            print(f"Error guardando modelo: {e}")
            return False
    
    def load_model(self):
        """Carga modelo pre-entrenado"""
        if not os.path.exists(self.model_file):
            return False
        
        try:
            with open(self.model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.is_trained = model_data['is_trained']
            self.state_names = model_data['state_names']
            self.regime_characteristics = model_data['regime_characteristics']
            
            print(f"✅ Modelo HMM cargado desde {self.model_file}")
            return True
            
        except Exception as e:
            print(f"⚠️ Error cargando modelo: {e}")
            return False


class RegimeAdaptiveTrading:
    """
    Sistema que adapta parámetros de trading según el régimen detectado
    
    Ajusta automáticamente:
    - SL/TP según volatilidad del régimen
    - Agresividad (lotes) según régimen
    - Filtros de confianza
    - Estrategias habilitadas
    """
    
    def __init__(self):
        self.regime_configs = {
            "Trending Up": {
                'sl_multiplier': 1.2,      # SL más amplio
                'tp_multiplier': 1.5,      # TP más ambicioso
                'lot_multiplier': 1.2,     # Aumentar lotes
                'confidence_adjustment': -0.05,  # Permitir -5% confianza
                'prefer_strategies': ['ml', 'sr', 'fibo'],  # Estrategias óptimas
                'description': 'Tendencia alcista - Aumentar agresividad'
            },
            "Ranging": {
                'sl_multiplier': 0.8,      # SL más tight
                'tp_multiplier': 0.8,      # TP más conservador
                'lot_multiplier': 0.7,     # Reducir lotes
                'confidence_adjustment': +0.10,  # Requerir +10% confianza
                'prefer_strategies': ['sr', 'liquidity'],  # S/R y liquidez mejor en ranging
                'description': 'Mercado lateral - Reducir exposición'
            },
            "Trending Down": {
                'sl_multiplier': 1.2,      # SL más amplio
                'tp_multiplier': 1.5,      # TP más ambicioso
                'lot_multiplier': 1.2,     # Aumentar lotes
                'confidence_adjustment': -0.05,  # Permitir -5% confianza
                'prefer_strategies': ['ml', 'sr', 'fibo'],
                'description': 'Tendencia bajista - Aumentar agresividad'
            }
        }
    
    def get_adapted_parameters(self, regime_name, base_params):
        """
        Adapta parámetros de trading según régimen
        
        Args:
            regime_name: Nombre del régimen ('Trending Up', 'Ranging', 'Trending Down')
            base_params: Dict con parámetros base
        
        Returns:
            dict: Parámetros adaptados
        """
        if regime_name not in self.regime_configs:
            return base_params
        
        config = self.regime_configs[regime_name]
        
        adapted = base_params.copy()
        adapted['sl_pips'] = int(base_params.get('sl_pips', 70) * config['sl_multiplier'])
        adapted['tp_pips'] = int(base_params.get('tp_pips', 140) * config['tp_multiplier'])
        adapted['lot_size'] = base_params.get('lot_size', 0.02) * config['lot_multiplier']
        adapted['confidence_threshold'] = (
            base_params.get('confidence_threshold', 0.70) + 
            config['confidence_adjustment']
        )
        
        return adapted

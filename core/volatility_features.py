"""
╔══════════════════════════════════════════════════════════════════════════╗
║           VOLATILITY FEATURES v1.0 - MEJORA ML CRÍTICA #2               ║
║                                                                          ║
║  3 Features críticos de volatilidad para mejorar predicciones ML        ║
║  - Parkinson Volatility (más eficiente que ATR)                         ║
║  - Garman-Klass Volatility (óptimo para mercado 24/7)                   ║
║  - Volatility Regime (detección high/normal/low)                        ║
║                                                                          ║
║  IMPACTO ESTIMADO: +3-5% accuracy en predicciones ML                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import numpy as np
import pandas as pd


class VolatilityFeatures:
    """
    Calculador de features avanzados de volatilidad
    
    Implementa 3 métricas críticas que capturan mejor la volatilidad
    que el ATR básico, especialmente para mercados 24/7 como XAUUSD.
    """
    
    def __init__(self, window=14):
        """
        Args:
            window: Período de ventana para cálculos (default: 14)
        """
        self.window = window
    
    def parkinson_volatility(self, df):
        """
        Parkinson Volatility - Estimador más eficiente que ATR
        
        Usa solo high y low, ignorando close. Es 5x más eficiente
        estadísticamente que la volatilidad de close-to-close.
        
        Formula: sqrt(1/(4*n*ln(2)) * sum((ln(H/L))^2))
        
        Args:
            df: DataFrame con columnas 'high' y 'low'
        
        Returns:
            Series: Parkinson volatility
        """
        # Calcular log ratio de high/low
        log_hl = np.log(df['high'] / df['low'])
        
        # Parkinson volatility
        parkinson = np.sqrt(
            1.0 / (4.0 * np.log(2.0)) * 
            log_hl.pow(2).rolling(window=self.window).mean()
        )
        
        return parkinson
    
    def garman_klass_volatility(self, df):
        """
        Garman-Klass Volatility - Óptimo para mercados 24/7
        
        Combina high, low, open, close para estimación más precisa.
        Es 8x más eficiente que volatilidad close-to-close.
        
        Args:
            df: DataFrame con OHLC
        
        Returns:
            Series: Garman-Klass volatility
        """
        # Componente 1: 0.5 * (ln(H/L))^2
        log_hl = np.log(df['high'] / df['low'])
        component1 = 0.5 * log_hl.pow(2)
        
        # Componente 2: -(2*ln(2) - 1) * (ln(C/O))^2
        log_co = np.log(df['close'] / df['open'])
        component2 = -(2 * np.log(2) - 1) * log_co.pow(2)
        
        # Garman-Klass volatility
        gk_volatility = np.sqrt(
            (component1 + component2).rolling(window=self.window).mean()
        )
        
        return gk_volatility
    
    def volatility_regime(self, df, parkinson_vol=None):
        """
        Volatility Regime Detection - Clasifica régimen de volatilidad
        
        Detecta 3 regímenes basándose en percentiles históricos:
        - Low volatility: < percentil 33
        - Normal volatility: percentil 33-67
        - High volatility: > percentil 67
        
        Args:
            df: DataFrame con OHLC
            parkinson_vol: Series con Parkinson vol (si ya calculado)
        
        Returns:
            Series: Régimen (0=low, 1=normal, 2=high)
        """
        # Usar Parkinson como medida base
        if parkinson_vol is None:
            parkinson_vol = self.parkinson_volatility(df)
        
        # Calcular percentiles en ventana móvil de 100 períodos
        lookback = 100
        
        def classify_regime(series):
            """Clasifica régimen basado en percentiles"""
            if len(series) < 10:
                return 1  # Normal por defecto
            
            current_vol = series.iloc[-1]
            percentile_33 = series.quantile(0.33)
            percentile_67 = series.quantile(0.67)
            
            if current_vol < percentile_33:
                return 0  # Low volatility
            elif current_vol > percentile_67:
                return 2  # High volatility
            else:
                return 1  # Normal volatility
        
        # Aplicar clasificación en rolling window
        regime = parkinson_vol.rolling(window=lookback, min_periods=20).apply(
            classify_regime, raw=False
        )
        
        return regime
    
    def calculate_all_features(self, df):
        """
        Calcula todos los features de volatilidad en un DataFrame
        
        Args:
            df: DataFrame con OHLC
        
        Returns:
            DataFrame: df original + nuevas columnas de volatilidad
        """
        df_copy = df.copy()
        
        # 1. Parkinson Volatility
        df_copy['parkinson_vol'] = self.parkinson_volatility(df)
        
        # 2. Garman-Klass Volatility
        df_copy['garman_klass_vol'] = self.garman_klass_volatility(df)
        
        # 3. Volatility Regime
        df_copy['volatility_regime'] = self.volatility_regime(
            df, 
            parkinson_vol=df_copy['parkinson_vol']
        )
        
        # 4. Ratio de volatilidades (feature adicional útil)
        df_copy['vol_ratio_gk_park'] = (
            df_copy['garman_klass_vol'] / 
            df_copy['parkinson_vol'].replace(0, np.nan)
        )
        
        # 5. Volatility momentum (cambio en volatilidad)
        df_copy['parkinson_vol_change'] = df_copy['parkinson_vol'].pct_change(5)
        
        return df_copy
    
    def get_features_for_ml(self, df):
        """
        Extrae solo las features de volatilidad listas para ML
        
        Args:
            df: DataFrame con features calculados
        
        Returns:
            dict: Features de volatilidad para modelo ML
        """
        if len(df) == 0:
            return {
                'parkinson_vol': 0.0,
                'garman_klass_vol': 0.0,
                'volatility_regime': 1,
                'vol_ratio_gk_park': 1.0,
                'parkinson_vol_change': 0.0
            }
        
        last_row = df.iloc[-1]
        
        return {
            'parkinson_vol': float(last_row.get('parkinson_vol', 0.0)),
            'garman_klass_vol': float(last_row.get('garman_klass_vol', 0.0)),
            'volatility_regime': int(last_row.get('volatility_regime', 1)),
            'vol_ratio_gk_park': float(last_row.get('vol_ratio_gk_park', 1.0)),
            'parkinson_vol_change': float(last_row.get('parkinson_vol_change', 0.0))
        }


class VolatilityRegimeAnalyzer:
    """
    Analizador especializado de régimen de volatilidad
    
    Proporciona información adicional sobre el régimen actual
    para toma de decisiones de trading.
    """
    
    def __init__(self):
        self.regime_names = {
            0: "Low Volatility",
            1: "Normal Volatility",
            2: "High Volatility"
        }
        
        self.regime_recommendations = {
            0: {
                'sl_multiplier': 0.75,
                'tp_multiplier': 0.85,
                'confidence_adjustment': +0.05,
                'description': 'Mercado tranquilo - Reducir riesgo'
            },
            1: {
                'sl_multiplier': 1.0,
                'tp_multiplier': 1.0,
                'confidence_adjustment': 0.0,
                'description': 'Mercado normal - Parámetros estándar'
            },
            2: {
                'sl_multiplier': 1.5,
                'tp_multiplier': 1.3,
                'confidence_adjustment': +0.10,
                'description': 'Mercado volátil - Aumentar prudencia'
            }
        }
    
    def get_regime_info(self, regime_value):
        """Obtiene información del régimen actual"""
        regime = int(regime_value)
        
        if regime not in [0, 1, 2]:
            regime = 1
        
        return {
            'regime': regime,
            'name': self.regime_names[regime],
            'recommendations': self.regime_recommendations[regime]
        }

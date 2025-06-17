import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class IndicatorCalculator:
    """Technical indicator calculator"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Default neutral RSI
        
        df = pd.DataFrame({'price': prices})
        delta = df['price'].diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    @staticmethod
    def calculate_moving_average(prices: List[float], period: int) -> float:
        """Calculate simple moving average"""
        if len(prices) < period:
            return float(np.mean(prices)) if prices else 0.0
        
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_volume_delta(volumes: List[float], period: int = 7) -> float:
        """Calculate volume delta (current vs average)"""
        if len(volumes) < 2:
            return 0.0
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-period:]) if len(volumes) >= period else np.mean(volumes[:-1])
        
        if avg_volume == 0:
            return 0.0
        
        return (current_volume - avg_volume) / avg_volume * 100
    
    @staticmethod
    def detect_breakout(prices: List[float], volumes: List[float], 
                       price_threshold: float = 0.05, volume_threshold: float = 2.0) -> bool:
        """Detect price breakout with volume confirmation"""
        if len(prices) < 2 or len(volumes) < 2:
            return False
        
        # Price breakout: current price > previous price by threshold
        price_change = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
        price_breakout = price_change > price_threshold
        
        # Volume confirmation: current volume > average volume by threshold
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        volume_surge = volumes[-1] / avg_volume if avg_volume > 0 else 1
        volume_confirmation = volume_surge > volume_threshold
        
        return price_breakout and volume_confirmation
    
    @staticmethod
    def calculate_holder_delta(holders: List[int], period: int = 7) -> float:
        """Calculate holder count delta"""
        if len(holders) < 2:
            return 0.0
        
        current_holders = holders[-1]
        avg_holders = np.mean(holders[-period:]) if len(holders) >= period else np.mean(holders[:-1])
        
        if avg_holders == 0:
            return 0.0
        
        return (current_holders - avg_holders) / avg_holders * 100

class TokenSignalCalculator:
    """Main class for calculating token signals"""
    
    def __init__(self):
        self.calculator = IndicatorCalculator()
    
    def calculate_indicators(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate all indicators for a token"""
        if not historical_data:
            return self._default_indicators()
        
        # Extract data series
        prices = [float(data.get('price_usd', 0)) for data in historical_data]
        volumes = [float(data.get('volume_24h', 0)) for data in historical_data]
        holders = [int(data.get('holders', 0)) for data in historical_data]
        
        # Calculate indicators
        rsi = self.calculator.calculate_rsi(prices)
        ma_7d = self.calculator.calculate_moving_average(prices, 7)
        ma_30d = self.calculator.calculate_moving_average(prices, 30)
        volume_delta = self.calculator.calculate_volume_delta(volumes)
        holder_delta = self.calculator.calculate_holder_delta(holders)
        breakout = self.calculator.detect_breakout(prices, volumes)
        
        return {
            'rsi': rsi,
            'ma_7d': ma_7d,
            'ma_30d': ma_30d,
            'volume_delta': volume_delta,
            'holder_delta': holder_delta,
            'breakout': breakout,
            'current_price': prices[-1] if prices else 0,
            'current_volume': volumes[-1] if volumes else 0
        }
    
    def _default_indicators(self) -> Dict[str, Any]:
        """Return default indicators when no data available"""
        return {
            'rsi': 50.0,
            'ma_7d': 0.0,
            'ma_30d': 0.0,
            'volume_delta': 0.0,
            'holder_delta': 0.0,
            'breakout': False,
            'current_price': 0.0,
            'current_volume': 0.0
        } 
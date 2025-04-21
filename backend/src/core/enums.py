from enum import Enum

class MarketCondition(str, Enum):
    """Possible market conditions"""
    NORMAL = "normal"
    VOLATILE = "volatile"
    BULL = "bull"
    BEAR = "bear" 
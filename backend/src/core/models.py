from pydantic import BaseModel, Field, root_validator, validator
from typing import Dict, Optional

class AnalyzePortfolioParams(BaseModel):
    """Parameters for portfolio analysis"""
    portfolio_id: int
    user_id: str = "current_user"
    include_sentiment: bool = True
    include_manipulation_check: bool = True
    
class ExecuteRebalanceParams(BaseModel):
    """Parameters for executing a portfolio rebalance"""
    portfolio_id: int
    user_id: str = "current_user"
    dry_run: bool = False  # If True, analyze but don't execute
    max_slippage_percent: float = Field(ge=0.1, le=5.0, default=1.0)
    
    @validator('max_slippage_percent')
    def validate_slippage(cls, v):
        if v < 0.1 or v > 5.0:
            raise ValueError('Slippage must be between 0.1% and 5.0%')
        return v
        
class SimulateRebalanceParams(BaseModel):
    """Parameters for simulating a portfolio rebalance"""
    portfolio_id: int
    user_id: str = "current_user"
    target_allocations: Dict[str, float] = Field(default_factory=dict)
    
    @root_validator(skip_on_failure=True)
    def validate_allocations(cls, values):
        allocations = values.get('target_allocations', {})
        if not allocations:
            raise ValueError('Target allocations must be provided')
            
        total = sum(allocations.values())
        if abs(total - 1.0) > 0.01:  # Allow small rounding errors
            raise ValueError(f'Target allocations must sum to 1.0 (got {total})')
            
        return values

class GetPerformanceParams(BaseModel):
    """Parameters for getting performance metrics"""
    portfolio_id: Optional[int] = None
    days: int = Field(ge=1, le=365, default=30)
    include_recommendations: bool = True
    
    @validator('days')
    def validate_days(cls, v):
        if v < 1 or v > 365:
            raise ValueError('Days must be between 1 and 365')
        return v

class EnableAutoRebalanceParams(BaseModel):
    """Parameters for enabling automatic rebalancing"""
    portfolio_name: str = "main"
    frequency: str = "daily"  # hourly, daily, weekly, monthly
    max_slippage: float = Field(ge=0.1, le=5.0, default=1.0)
    
    @validator('max_slippage')
    def validate_slippage(cls, v):
        if v < 0.1 or v > 5.0:
            raise ValueError('Slippage must be between 0.1% and 5.0%')
        return v
        
class DisableAutoRebalanceParams(BaseModel):
    """Parameters for disabling automatic rebalancing"""
    portfolio_name: str = "main"
    
class GetRebalancingStatusParams(BaseModel):
    """Parameters for getting rebalancing status"""
    portfolio_name: str = "main" 
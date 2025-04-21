import abc
from typing import Dict, Any, List, Optional, Union

# Forward declaration for type hints if needed later
EvmWalletProvider = Any

class IDatabaseManager(abc.ABC):
    """Interface for database operations relevant to core logic."""
    @abc.abstractmethod
    async def initialize(self) -> None:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass

    @abc.abstractmethod
    async def get_portfolio(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def update_portfolio(self, portfolio_id: int, update_data: Dict[str, Any]) -> None:
        # Specific method might be needed for rebalancing updates
        pass

    @abc.abstractmethod
    async def log_portfolio_event(self, portfolio_id: int, event_type: str, details: Optional[str] = None) -> None:
        pass

    @abc.abstractmethod
    async def get_asset_historical_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        # Added days parameter based on typical usage
        pass

    # Add other essential CRUD methods if needed by multiple core components

class IIntelligenceEngine(abc.ABC):
    """Interface for intelligence and analysis operations."""
    @abc.abstractmethod
    async def analyze_portfolio(self, user_id: str, portfolio_id: int) -> Dict[str, Any]:
        pass
        
    # Added methods based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def get_asset_sentiments(self, assets: List[str], days: int = 30) -> Dict[str, Any]:
        pass
        
    @abc.abstractmethod
    async def check_manipulation(self, assets: List[str]) -> Dict[str, Any]:
        pass
        
    @abc.abstractmethod
    async def project_with_sentiment(self, portfolio_id: int, target_allocations: Dict[str, float], days: int) -> Dict[str, Any]:
        pass
        
    # Method based on usage in RebalancerActionProvider
    @abc.abstractmethod
    async def get_portfolio(self, user_id: str, portfolio_id: int) -> Optional[Dict[str, Any]]:
         # This duplicates db_manager.get_portfolio - consider if needed at intelligence level
        pass


class IStrategyEngine(abc.ABC):
    """Interface for strategy execution and statistical analysis."""
    @abc.abstractmethod
    async def analyze_portfolio_statistics(self, portfolio_id: int) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def execute_rebalance(self, user_id: str, portfolio_id: int, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def calculate_rebalancing_costs(self, portfolio: Dict[str, Any]) -> Dict[str, float]:
        pass
        
    # Added method based on usage in RebalancerActionProvider
    @abc.abstractmethod
    async def analyze_portfolio(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Note: Original implementation might differ, check StrategyEngine
        pass
        
    # Added method based on usage in RebalancerActionProvider
    @abc.abstractmethod
    async def get_market_condition(self) -> str:
         # Note: Original implementation might differ, check StrategyEngine
        pass
        
    # Added method based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def _calculate_required_trades(self, portfolio: Dict[str, Any], target_allocations: Dict[str, float]) -> List[Dict[str, Any]]:
        # Note: Usually private, exposed via simulate_rebalance? Interface needs care.
        pass


class ITradeReviewer(abc.ABC):
    """Interface for reviewing and validating trades."""
    @abc.abstractmethod
    async def review_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]: # Assuming ReviewResult can be simplified to Dict
        pass

    @abc.abstractmethod
    async def validate_rebalance_plan(self, assets: List[Dict[str, Any]], market_condition: str) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def bulk_review(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

class IPerformanceAnalyzer(abc.ABC):
    """Interface for performance tracking and analysis."""
    @abc.abstractmethod
    async def log_rebalance(self, rebalance_data: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    async def update_trade_outcome(self, log_id: int, exit_price: float) -> None:
        pass

    @abc.abstractmethod
    async def analyze_performance(self, portfolio_id: Optional[int] = None) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def generate_performance_report(self, days: int = 30) -> str:
        pass
        
    # Added based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def get_portfolio_performance(self, portfolio_id: int, include_sentiment_impact: bool) -> Dict[str, Any]:
        # Note: Implementation likely exists in PerformanceAnalyzer, adjust if needed
        pass
        
    # Added based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def get_sentiment_correlation(self, portfolio_id: int, days: int) -> Dict[str, Any]:
        # Note: Implementation likely exists in PerformanceAnalyzer, adjust if needed
        pass


class ITradeExecutionProvider(abc.ABC):
    """Interface for executing trades (buy, sell, swap)."""
    # Define common execution methods based on Rebalancer and Kuru needs
    # These might need refinement based on how execution is generalized

    @abc.abstractmethod
    async def execute_buy(self, user_id: str, symbol: str, amount: float, max_slippage_percent: float, order_type: str = 'market', price: Optional[float] = None) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def execute_sell(self, user_id: str, symbol: str, amount: float, max_slippage_percent: float, order_type: str = 'market', price: Optional[float] = None) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def execute_swap(self, user_id: str, from_token: str, to_token: str, amount_in: float, max_slippage_percent: float, market_id: str) -> Dict[str, Any]:
        # Specific to swap functionality, might be optional for some providers
        pass

    @abc.abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        pass

    # Consider adding methods for limit orders, cancellation etc. if universally needed

class IKuruTradeExecutionProvider(ITradeExecutionProvider): # Inherits common methods
    """Specific interface for Kuru DEX interactions, extending base execution."""
    # Kuru-specific methods identified from KuruActionProvider

    @abc.abstractmethod
    def place_limit_order(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
         # Note: ActionProvider methods are sync, might need async wrappers or refactor
        pass

    @abc.abstractmethod
    def cancel_order(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def batch_orders(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def deposit_margin(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def view_margin_balance(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def get_orderbook(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def get_portfolio(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
         # Kuru-specific portfolio view
        pass

class IRebalancer(abc.ABC): # Distinct from ITradeExecutionProvider, as it orchestrates
    """Interface for the high-level rebalancing orchestrator."""
    @abc.abstractmethod
    def analyze_portfolio(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        # Note: ActionProvider methods are sync, might need async wrappers or refactor
        pass

    @abc.abstractmethod
    def execute_rebalance(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def simulate_rebalance(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    @abc.abstractmethod
    def get_performance(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        pass

    # Add auto-rebalance control methods if considered core interface
    # @abc.abstractmethod
    # def enable_auto_rebalance(self, ...) -> str:
    #     pass
    # @abc.abstractmethod
    # def disable_auto_rebalance(self, ...) -> str:
    #     pass
    # @abc.abstractmethod
    # def get_rebalancing_status(self, ...) -> str:
    #     pass 

# Add IRiskManager interface
class IRiskManager(abc.ABC):
    """Interface for risk management operations."""
    @abc.abstractmethod
    async def assess_portfolio_risk(self, portfolio_id: int) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def validate_rebalance_plan(self, portfolio_id: int, target_allocations: Dict[str, float]) -> Dict[str, Any]:
        pass
        
    # Added based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def project_portfolio_performance(self, portfolio_id: int, target_allocations: Dict[str, float], days: int) -> Dict[str, Any]:
        # Note: Implementation likely exists in RiskManager, adjust if needed
        pass


# Add IYieldOptimizer interface
class IYieldOptimizer(abc.ABC):
    """Interface for yield optimization operations."""
    @abc.abstractmethod
    async def find_opportunities(self, portfolio_id: int) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def optimize_yields(self, portfolio_id: int) -> Dict[str, Any]:
        pass
        
    # Added based on usage in PortfolioActionProvider
    @abc.abstractmethod
    async def _calculate_optimal_allocation(self, opportunities: List[Dict[str, Any]], portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
         # Note: Usually private, exposed via optimize_yields? Interface needs care.
        pass


from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime

import pandas as pd
# No longer need TYPE_CHECKING for AgentKitClient if not injected here
# from typing import TYPE_CHECKING

# Import Interfaces using absolute paths
from src.core.interfaces import IIntelligenceEngine, IDatabaseManager, IStrategyEngine

# Keep concrete imports for components without interfaces yet or not injected here
from .allora.client import AlloraClient
from .allora.models import SentimentAnalysis, FearGreedIndex, MarketManipulation, RebalanceSignal, AssetAnalysisResult
from .allora.config import get_asset_profile, AlloraConfig
from .market_analysis import MarketAnalyzer
from .market_data import MarketDataAnalyzer
from .agent_kit.client import AgentKitClient # Keep if used directly and not injected via interface

# if TYPE_CHECKING:
#     from .agent_kit.client import AgentKitClient

logger = logging.getLogger(__name__)

class IntelligenceEngine(IIntelligenceEngine): # Implement interface
    #  Strategy engine that combines AI predictions from Allora
    # with statistical analysis as recommended by Rose Heart.
    """
    Strategy engine implementing Rose Heart's advice:
    - AI for sentiment analysis only
    - Statistical methods for numerical computations
    - Equal weighting to start (refined through testing)
    """
    
    def __init__(
        self, 
        allora_client: AlloraClient, # Keep concrete hint
        market_analyzer: MarketAnalyzer, # Keep concrete hint
        agent_kit_client: Optional[AgentKitClient] = None, # Keep concrete hint if needed directly
        market_data_service: Optional[MarketDataAnalyzer] = None, # Keep concrete hint
        config: Optional[Dict[str, Any]] = None, # Use Optional
        db_manager: Optional[IDatabaseManager] = None, # Use interface hint
        strategy_engine: Optional[IStrategyEngine] = None # Use interface hint
    ):
        self.allora_client = allora_client
        self.market_analyzer = market_analyzer
        self.agent_kit_client = agent_kit_client
        self.market_data_service = market_data_service
        self.config = config or {}
        self.db_manager: Optional[IDatabaseManager] = db_manager
        self.strategy_engine: Optional[IStrategyEngine] = strategy_engine

        #  # Map of assets to Allora topic IDs
        # self.topic_mappings = {
        #     "BTC": 14,
        #     "ETH": 13,
        #     # Add other assets as needed
        
        # Initial equal weights as Rose Heart suggested
        self.weights = {
            "sentiment": 0.25,
            "below_median": 0.25,
            "volatility": 0.25,
            "trend": 0.25
        }

        # Performance tracking for self-improvement
        self.performance_history = {}

    #            # Weights for different signals (statistical vs AI)
    #     # Starting with equal weights as Rose Heart suggested
    #     self.signal_weights = {
    #         "allora_prediction": 0.25,
    #         "statistical_metrics": 0.25,
    #         "market_sentiment": 0.25,
    #         "technical_indicators": 0.25
    #     }
        
    # async def generate_portfolio_recommendation(
    #     self,
    #     portfolio: Dict[str, float],
    #     current_prices: Dict[str, float],
    #     historical_data: Dict[str, Any]
    # ) -> Dict[str, Any]:
    
    async def analyze_portfolio(self, user_id: str, portfolio_id: int) -> Dict[str, Any]:
        """
        Analyze portfolio and determine if rebalancing is needed
        
        Implements the dual approach from Rose Heart:
        - AI for sentiment analysis (Allora)
        - Statistical methods for numerical analysis
        """
        if not self.db_manager or not self.strategy_engine:
             logger.warning("IntelligenceEngine requires db_manager and strategy_engine for analysis.")
             return {"error": "Missing dependencies"}
             
        try:
            # Get portfolio data using interface attribute
            portfolio = await self.db_manager.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": f"Portfolio {portfolio_id} not found"}
            
            # Get statistical metrics from Strategy Engine using interface attribute
            stats = await self.strategy_engine.analyze_portfolio_statistics(portfolio_id)
            
            # Get sentiment analysis from Allora
            sentiment_analysis = await self.allora_client.analyze_sentiment(
                assets=[asset["symbol"] for asset in portfolio.get("assets", [])]
            )
            
            # Get fear/greed index from Allora
            fear_greed = await self.allora_client.get_fear_greed_index(
                assets=[asset["symbol"] for asset in portfolio.get("assets", [])]
            )
            
            # Check for market manipulation
            manipulation = await self.allora_client.detect_market_manipulation(
                assets=[asset["symbol"] for asset in portfolio.get("assets", [])]
            )
            
            # Combine signals with equal weights as recommended by Rose Heart
            combined_signals = self._combine_signals(
                sentiment=sentiment_analysis,
                fear_greed=fear_greed,
                manipulation=manipulation,
                stats=stats
            )
            
            # Calculate rebalancing costs using interface attribute
            rebalancing_costs = await self.strategy_engine.calculate_rebalancing_costs(portfolio)
            
            # Calculate potential benefits based on combined signals
            potential_benefits = self._calculate_potential_benefits(
                portfolio=portfolio,
                combined_signals=combined_signals,
                stats=stats
            )
            
            # Determine if rebalancing is recommended (2x cost/benefit ratio per Rose Heart)
            rebalance_recommended = potential_benefits > (rebalancing_costs["total_cost"] * 2)
            
            # Generate target allocations if rebalancing is recommended
            target_allocations = self._generate_target_allocations(
                portfolio=portfolio,
                combined_signals=combined_signals,
                stats=stats
            ) if rebalance_recommended else {}
            
            # Prepare recommendation
            recommendation = {
                "portfolio_id": portfolio_id,
                "rebalance_recommended": rebalance_recommended,
                "reason": "Benefits significantly exceed costs" if rebalance_recommended else "Costs exceed benefits",
                "potential_benefits": potential_benefits,
                "rebalancing_costs": rebalancing_costs,
                "target_allocations": target_allocations,
                "sentiment_analysis": sentiment_analysis,
                "fear_greed_index": fear_greed,
                "manipulation_detected": any(m.get("detected", False) for m in manipulation.values()),
                "statistical_metrics": stats
            }
            
            return recommendation
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {str(e)}")
            return {
                "portfolio_id": portfolio_id,
                "rebalance_recommended": False,
                "error": str(e),
                "message": "Error analyzing portfolio"
            }
    
    def _calculate_combined_score(
        self, 
        sentiment_data: Dict[str, Any],
        stats_data: Dict[str, Any],
        asset_profile: Any
    ) -> float:
        """
        Calculate combined score from sentiment and statistical data
        using asset-specific weights
        """
        score = 0.0
        
        # 1. Sentiment contribution
        primary_emotion = sentiment_data.get("primary_emotion")
        if primary_emotion == "greed":
            score += asset_profile.sentiment_weight
        elif primary_emotion == "fear":
            score -= asset_profile.sentiment_weight
            
        # 2. Below median frequency contribution
        below_median = stats_data.get("below_median_frequency", 0.5)
        if below_median < 0.4:  # Price frequently above median
            score += self.weights["below_median"] * asset_profile.statistical_weight
        elif below_median > 0.6:  # Price frequently below median
            score -= self.weights["below_median"] * asset_profile.statistical_weight
        
        # 3. Volatility contribution - penalize high volatility
        volatility = stats_data.get("volatility", 0.5)
        vol_normalized = min(1.0, volatility / 0.8)  # Cap at 1.0
        score -= vol_normalized * self.weights["volatility"] * asset_profile.statistical_weight
            
        # 4. Trend contribution
        if stats_data.get("trend") == "uptrend":
            score += self.weights["trend"] * asset_profile.statistical_weight
        else:
            score -= self.weights["trend"] * asset_profile.statistical_weight
            
        # Normalize score to range -1.0 to 1.0
        return max(-1.0, min(1.0, score))
    
    def _calculate_target_weight(
        self,
        current_weight: float,
        combined_score: float,
        sentiment_data: Dict[str, Any],
        stats_data: Dict[str, Any]
    ) -> float:
        """Calculate target weight based on current weight and combined score"""
        # Base adjustment on the combined score
        # Score range is -1.0 to 1.0
        adjustment_factor = 0.2  # Maximum 20% adjustment
        
        # Calculate adjustment as percentage of current weight
        adjustment = current_weight * adjustment_factor * combined_score
        
        # Calculate new weight
        new_weight = current_weight + adjustment
        
        # Ensure weight is between 0.05 (5%) and 0.8 (80%)
        # Rose Heart advised to keep 20% in stablecoins
        new_weight = max(0.05, min(0.8, new_weight))
        
        return new_weight
        
    def _analyze_rebalance_costs(
        self,
        portfolio: Dict[str, Any],
        assets_analysis: List[AssetAnalysisResult]
    ) -> Dict[str, Any]:
        """
        Analyze the costs and benefits of rebalancing
        
        Rose Heart emphasized not rebalancing too frequently due to fees
        """
        # Get current holdings and prices
        holdings = {a["symbol"]: a.get("amount", 0) for a in portfolio.get("assets", [])}
        weights = {a["symbol"]: a.get("weight", 0) for a in portfolio.get("assets", [])}
        prices = {a["symbol"]: a.get("price", 0) for a in portfolio.get("assets", [])}
        
        # Calculate total portfolio value
        total_value = sum(holdings.get(a, 0) * prices.get(a, 0) for a in holdings)
        
        # Calculate required trades
        trades = {}
        for asset_analysis in assets_analysis:
            symbol = asset_analysis.asset
            current_weight = weights.get(symbol, 0)
            target_weight = asset_analysis.rebalance_signal.target_weight
            
            if abs(target_weight - current_weight) < 0.01:
                continue  # Skip small changes
                
            # Calculate trade amount
            current_value = total_value * current_weight
            target_value = total_value * target_weight
            value_change = target_value - current_value
            
            if abs(value_change) < 10:  # Skip very small trades
                continue
                
            price = prices.get(symbol, 0)
            if price <= 0:
                continue
                
            amount_change = value_change / price
            
            trades[symbol] = {
                "symbol": symbol,
                "amount": amount_change,
                "value": value_change,
                "price": price,
                "weight_change": target_weight - current_weight
            }
        
        # Calculate estimated costs (fees)
        fee_rate = self.config.get("FEE_RATE", 0.001)  # Default 0.1%
        estimated_fees = sum(abs(t["value"]) * fee_rate for t in trades.values())
        
        # Calculate potential benefit
        # This is a simplified estimate based on expected weight optimization
        potential_benefit = total_value * 0.01  # Assume 1% improvement
        for trade in trades.values():
            # Add benefit from adjusting to improved weights
            symbol = trade["symbol"]
            for asset_analysis in assets_analysis:
                if asset_analysis.asset == symbol:
                    # Higher confidence = higher potential benefit
                    confidence = asset_analysis.rebalance_signal.confidence
                    # Adjust based on the confidence in the signal
                    potential_benefit += abs(trade["value"]) * (confidence - 0.5) * 0.04
        
        return {
            "total_portfolio_value": total_value,
            "num_trades": len(trades),
            "trades": list(trades.values()),
            "estimated_cost": estimated_fees,
            "potential_benefit": potential_benefit,
            "cost_effective": potential_benefit > estimated_fees * 2,  # 2x threshold
            "net_benefit": potential_benefit - estimated_fees
        }
            
    async def get_portfolio(self, user_id: str, portfolio_id: int) -> Dict[str, Any]:
        """Get portfolio data"""
        # This method uses self.db_manager which is now typed with the interface
        # Check if db_manager is available
        if not self.db_manager:
            logger.warning("Database manager not configured, cannot get portfolio.")
            return {"error": "Database manager not configured"}
            
        try:
            portfolio_data = await self.db_manager.get_portfolio(portfolio_id)
            return portfolio_data if portfolio_data else {"error": "Portfolio not found"}
        except Exception as e:
            logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
            return {"error": str(e)}

    # Ensure all abstract methods from IIntelligenceEngine are implemented
    # (analyze_portfolio)

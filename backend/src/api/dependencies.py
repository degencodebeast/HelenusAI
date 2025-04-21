from fastapi import Depends, FastAPI
import logging
from typing import List, Dict, Any, Optional

# from rebalancr.intelligence.reviewer import TradeReviewer

from src.intelligence.intelligence_engine import IntelligenceEngine
from src.intelligence.market_analysis import MarketAnalyzer
from src.database.db_manager import DatabaseManager
from src.intelligence.agent_kit.service import AgentKitService
from src.intelligence.allora.client import AlloraClient
from src.strategy.engine import StrategyEngine
from src.websockets.websocket_manager import WebSocketManager, websocket_manager
from src.services.chat_service import ChatService

from src.config import get_settings, Settings
from src.intelligence.agent_kit.wallet_provider import PrivyWalletProvider, get_wallet_provider

# Chat and service imports
from src.chat.history_manager import ChatHistoryManager
from src.services.market import MarketDataService

# Strategy imports
from src.strategy.risk_manager import RiskManager
from src.strategy.yield_optimizer import YieldOptimizer
from src.strategy.wormhole import WormholeService

# Agent imports
from src.intelligence.agent_kit.agent_manager import AgentManager
from src.intelligence.agent_kit.client import AgentKitClient

# Analytics imports
from src.performance.analyzer import PerformanceAnalyzer

# Core imports
from src.intelligence.reviewer import TradeReviewer
from src.execution.providers.kuru.kuru_action_provider import KuruActionProvider
from src.execution.providers.rebalancer.rebalancer_action_provider import RebalancerActionProvider

# Interfaces
from src.core.interfaces import (
    IDatabaseManager, IIntelligenceEngine, IStrategyEngine, 
    ITradeReviewer, IPerformanceAnalyzer, IKuruTradeExecutionProvider, 
    IRebalancer, ITradeExecutionProvider, # Base execution interface
    IRiskManager, IYieldOptimizer # Add new interfaces
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application_services() -> Dict[str, Any]:
    """
    Creates and wires up all application services using Dependency Injection.
    This is the single composition root.
    """
    logger.info("Creating application services...")
    
    # 1. Configuration
    config: Settings = get_settings()

    # 2. Core Components Instantiation
    db_manager: IDatabaseManager = DatabaseManager(db_path=config.DATABASE_URL)
    
    allora_client = AlloraClient(api_key=config.ALLORA_API_KEY) # Keep concrete for now
    
    market_analyzer = MarketAnalyzer() # Keep concrete for now
    
    market_data_service = MarketDataService(config) # Keep concrete for now
    
    # Assumes RiskManager constructor takes (db_manager, config)
    risk_manager: IRiskManager = RiskManager(db_manager, config) # Keep concrete for now
    
    # Assumes YieldOptimizer constructor takes (db_manager, market_data_service, config)
    yield_optimizer: IYieldOptimizer = YieldOptimizer(db_manager, market_data_service, config) # Keep concrete for now
    
    # Assumes WormholeService constructor takes (config)
    wormhole_service = WormholeService(config) # Keep concrete for now

    performance_analyzer: IPerformanceAnalyzer = PerformanceAnalyzer(db_manager=db_manager)
    
    # Assumes TradeReviewer constructor takes (config)
    trade_reviewer: ITradeReviewer = TradeReviewer(config=config.dict()) # Pass config as dict if needed
    
    strategy_engine: IStrategyEngine = StrategyEngine(
        db_manager=db_manager, 
        risk_manager=risk_manager, 
        yield_optimizer=yield_optimizer, 
        wormhole_service=wormhole_service,
        config=config.dict()
        # intelligence_engine will be set later if needed, but ideally removed
    )
    
    # Intelligence Engine depends on several components
    intelligence_engine: IIntelligenceEngine = IntelligenceEngine(
            allora_client=allora_client,
            market_analyzer=market_analyzer,
            market_data_service=market_data_service,
        config=config.dict(),
        db_manager=db_manager,
        strategy_engine=strategy_engine 
        # agent_kit_client will be set later if needed
    )
    # If StrategyEngine still needs IntelligenceEngine (circular dependency)
    # This should ideally be removed by further refactoring using interfaces/callbacks
    # strategy_engine.intelligence_engine = intelligence_engine 

    # 3. Wallet Provider
    # Assuming PrivyWalletProvider is the primary one and uses singleton pattern internally
    wallet_provider = PrivyWalletProvider.get_instance(config) 

    # 4. Execution Providers
    # Kuru provider - constructor takes Optional dicts
    kuru_provider: IKuruTradeExecutionProvider = KuruActionProvider(
        # Pass relevant config if needed, e.g., from config.dict() or specific settings
        # rpc_url_by_chain_id=config.KURU_RPC_URLS, 
        # margin_account_by_chain=config.KURU_MARGIN_ACCOUNTS
    ) 
    
    rebalancer_provider: IRebalancer = RebalancerActionProvider(
        wallet_provider=wallet_provider,
        intelligence_engine=intelligence_engine,
        strategy_engine=strategy_engine,
        trade_reviewer=trade_reviewer,
        performance_analyzer=performance_analyzer,
        db_manager=db_manager,
        kuru_provider=kuru_provider,
        # context=... # Context might need to be set dynamically
        config=config.dict()
    )

    # 5. AgentKit Components
    # AgentManager depends on config, db_manager, wallet_provider
    agent_manager = AgentManager(
        config=config,
        db_manager=db_manager, # Pass the instance
        wallet_provider=wallet_provider # Pass the instance
    )
    # Initialize agent_manager's internal service link if needed (check AgentManager.__init__)
    # agent_manager.initialize_service_dependency(...) 
    
    # AgentKitClient depends on config, agent_manager
    # If it still needs intelligence_engine, pass it; otherwise, None
    agent_kit_client = AgentKitClient(
         config=config.dict(), 
            agent_manager=agent_manager,
         intelligence_engine=intelligence_engine # Pass if needed, ideally remove
    )
    # Link intelligence engine back if needed (ideally remove)
    # intelligence_engine.agent_kit_client = agent_kit_client 
    
    # AgentKitService depends on config, wallet_provider, agent_manager
    # It also needs the action providers (rebalancer, kuru)
    agent_kit_service = AgentKitService(
         config=config, 
         wallet_provider=wallet_provider, 
         agent_manager=agent_manager,
         # Pass action providers directly
         action_providers=[rebalancer_provider, kuru_provider] 
    )
    # If AgentManager needs service (circular dependency?)
    # agent_manager.set_service(agent_kit_service) # Example, check actual method

    # 6. Other Services
    chat_history_manager = ChatHistoryManager(db_manager=db_manager) # Keep concrete for now
    
    # ChatService depends on db, agent_manager, websocket_manager
    chat_service = ChatService(
            db_manager=db_manager,
        agent_manager=agent_manager,
        websocket_manager=websocket_manager # Use imported singleton
    )

    logger.info("Application services created successfully.")
    
    # Return all created services in a dictionary
    return {
        "config": config,
        "db_manager": db_manager,
        "allora_client": allora_client,
        "market_analyzer": market_analyzer,
        "market_data_service": market_data_service,
        "risk_manager": risk_manager,
        "yield_optimizer": yield_optimizer,
        "wormhole_service": wormhole_service,
        "performance_analyzer": performance_analyzer,
        "trade_reviewer": trade_reviewer,
        "strategy_engine": strategy_engine,
        "intelligence_engine": intelligence_engine,
        "wallet_provider": wallet_provider,
        "kuru_provider": kuru_provider,
        "rebalancer_provider": rebalancer_provider,
        "agent_manager": agent_manager,
        "agent_kit_client": agent_kit_client,
        "agent_kit_service": agent_kit_service,
        "chat_history_manager": chat_history_manager,
        "chat_service": chat_service,
        "websocket_manager": websocket_manager # Include existing singleton if needed elsewhere
    }

def initialize_services(app: FastAPI):
    """Initialize all services and attach to app state"""
    # Initialize core services
    services = create_application_services()
    
    # Attach to app state
    app.state.db_manager = services["db_manager"]
    app.state.allora_client = services["allora_client"]
    app.state.agent_service = services["agent_kit_service"]
    app.state.agent_manager = services["agent_manager"]
    app.state.agent_kit_client = services["agent_kit_client"]
    app.state.intelligence_engine = services["intelligence_engine"]
    app.state.market_analyzer = services["market_analyzer"]
    app.state.strategy_engine = services["strategy_engine"]
    app.state.market_data_service = services["market_data_service"]
    app.state.risk_manager = services["risk_manager"]
    app.state.yield_optimizer = services["yield_optimizer"]
    app.state.chat_service = services["chat_service"]
    app.state.websocket_manager = services["websocket_manager"]
    app.state.wallet_provider = get_wallet_provider()
    
    return app
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
import logging
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import initialize_services

from ..tasks.background_tasks import monitor_portfolios

from ..config import get_settings, Settings
from ..websockets.websocket_handlers import handle_websocket
from coinbase_agentkit import AgentKit, AgentKitConfig
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from .middleware.privy_auth import privy_auth_middleware

import sys
import re

# Configure root logger to show detailed logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s',
    stream=sys.stderr
)

# Configure logging
logger = logging.getLogger(__name__)

# Load configuration
config = get_settings()

# Initialize application
app = FastAPI(title="Rebalancr API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Privy authentication middleware
app.middleware("http")(privy_auth_middleware)

# Initialize and attach services to app.state
# This now uses the single composition root from dependencies.py
app = initialize_services(app)

#check whether this is correct or if I need to change it to a different endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)

# Include routers
#app.include_router(auth.router)
#app.include_router(chat_routes.router)
#app.include_router(websocket_routes.router, tags=["websocket"])
#app.include_router(wallet_routes.router)


# At the end of your app initialization
@app.on_event("startup")
async def startup_event():
    """Initialize the database and run migrations"""
    # Database initialization (db_manager is already on app.state)
    if hasattr(app.state, 'db_manager') and app.state.db_manager:
        await app.state.db_manager.initialize()
    else:
        logger.error("Database manager not found in app state during startup.")
        # Handle error appropriately, maybe raise exception?
        return 

    # Start portfolio monitoring in background (uses services from app.state)
    if hasattr(app.state, 'strategy_engine') and app.state.strategy_engine:
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            monitor_portfolios, 
            app.state.db_manager, 
            app.state.strategy_engine
        )
        # Need to figure out how to run background tasks from startup event
        # This might require a different approach like APScheduler or arq
        logger.info("Portfolio monitoring task added (execution depends on framework setup).")
    else:
        logger.warning("Strategy engine not found in app state, cannot start portfolio monitoring.")
    
    # Services are already initialized by initialize_services calling create_application_services
    # No need to call initialize_intelligence_services() here anymore
    # from .dependencies import initialize_intelligence_services
    # initialize_intelligence_services()

    # AgentKit Service finalization (if needed)
    # Access the service instance from app.state
    if hasattr(app.state, 'agent_service') and app.state.agent_service:
        service = app.state.agent_service # Get service from state
        
        # Log basic info before initialization
        logger.info("STARTUP: Completing AgentKitService initialization if needed.")
        
        # If AgentKitService needs specific post-init steps, call them here.
        # The example _complete_rebalancer_initialization might be internal to AgentKitService now
        # Check if service._complete_rebalancer_initialization() still exists/is needed
        if hasattr(service, '_complete_rebalancer_initialization') and callable(service._complete_rebalancer_initialization):
             service._complete_rebalancer_initialization()
             logger.info("AgentKitService._complete_rebalancer_initialization() called.")
        
        # Log available tools from AgentKitService
        if hasattr(service, 'tools'):
            tool_names = [t.name for t in service.tools]
            logger.info(f"Available AgentKit tools: {tool_names}")
            rebalancer_tools = [name for name in tool_names if name.startswith('rebalancer')]
            if rebalancer_tools:
                logger.info(f"Rebalancer tools found: {rebalancer_tools}")
            else:
                logger.warning("No tools with 'rebalancer' prefix found in AgentKitService.")
        else:
             logger.warning("AgentKitService instance does not have a 'tools' attribute.")
    else:
        logger.error("AgentKitService (agent_service) not found in app state during startup.")

@app.on_event("shutdown")
async def shutdown_db():
    """Close database connections on shutdown"""
    if hasattr(app.state, 'db_manager') and app.state.db_manager:
        await app.state.db_manager.close()
    else:
        logger.warning("Database manager not found in app state during shutdown.")

@app.get("/")
async def home():
    return {
        "name": "Rebalancr API",
        "status": "online",
        "version": "0.1.0",
        "docs": "/docs"  # Link to FastAPI's automatic docs
    }

# Remove old WebSocket endpoint example code if it exists below
# ... (old commented out WebSocket code removed) ...

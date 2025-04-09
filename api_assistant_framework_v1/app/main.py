# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware

from app.config import settings, logger
# --- Import Routers ---
from app.api.v1.endpoints import chat
from app.api.v1.endpoints import operations # Import the new operations router
# --- Import Engine and Parser ---
from app.core.api_parser import APISpecParser
from app.core.flow_engine import DialogFlowEngine
# --- Import DB Init ---
from app.db.database import init_db

# Define Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    # --- Initialize Database ---
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize database: {e}", exc_info=True)

    # --- Create Parser and Engine Instances ---
    app.state.api_parser = None # Initialize state attributes
    app.state.dialog_engine = None
    try:
        api_parser = APISpecParser(settings.API_SPEC_FILE)
        app.state.api_parser = api_parser # Store parser instance
        app.state.dialog_engine = DialogFlowEngine(api_parser=api_parser) # Pass parser to engine
        logger.info("API Parser and Dialog Engine initialized successfully.")
        # --- ADDED LOG ---
        logger.info(f"app.state contents after init: api_parser={type(app.state.api_parser)}, dialog_engine={type(app.state.dialog_engine)}")
        logger.debug(f"Available attributes in app.state after init: {dir(app.state)}")
        # --- END ADDED LOG ---
    except Exception as e:
        logger.error(f"CRITICAL: Failed to initialize core engine components: {e}", exc_info=True)
        # Ensure attributes exist even if None
        app.state.api_parser = None
        app.state.dialog_engine = None

    logger.info("Chat Assistant Framework Initialized.")
    yield
    # Actions on shutdown
    logger.info("Application shutdown...")
    app.state.dialog_engine = None
    app.state.api_parser = None

# Create FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME + " & Chat Assistant",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add CORS Middleware (origins might need adjustment)
origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix=settings.API_V1_STR + "/chat", tags=["Chat Assistant"])
app.include_router(operations.router, prefix=settings.API_V1_STR + "/operations", tags=["API Operations"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the API Chat Assistant Backend"}


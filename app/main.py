from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import settings
from app.core.observability import observability
from app.db.session import init_db
from app.api.complaints import router as complaints_router

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING level for prod
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("application_starting", environment=settings.ENVIRONMENT)
    
    # Initialize observability
    observability.initialize(app)
    
    # Initialize database
    await init_db()
    
    logger.info("application_started")
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    observability.flush()


app = FastAPI(
    title="CivicOps AI",
    description="Multi-agent pipeline for processing citizen infrastructure complaints",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(complaints_router, prefix="/api/v1", tags=["complaints"])


@app.get("/")
async def root():
    return {
        "name": "CivicOps AI",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }
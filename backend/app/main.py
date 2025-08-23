from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from .config import settings
from .database import engine, Base
from .routers import auth, calls, dashboard, projects
from .scheduler import start_scheduler
from .seeder import seed_demo_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting QA System API...")
    
    # Temporarily disable database and scheduler for debugging
    # Base.metadata.create_all(bind=engine)
    # logger.info("Database tables created")
    
    # if settings.auto_seed_demo:
    #     logger.info("Seeding demo data...")
    #     seed_demo_data()
    
    # start_scheduler()
    # logger.info("Background scheduler started")
    
    logger.info("QA System API started successfully (minimal mode)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down QA System API...")

app = FastAPI(
    title="AI Call Center QA System",
    description="Automated quality assurance for call center interactions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(calls.router, prefix="/calls", tags=["calls"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])

@app.get("/")
async def root():
    return {"message": "AI Call Center QA System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    # Return current UTC timestamp
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

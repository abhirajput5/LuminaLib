from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.settings import settings
from app.async_db import init_pool, close_pool
from app.api.auth.routes import router as auth_router
from app.api.books.routes import router as books_router
from app.logger import LoggerFactory

LoggerFactory.configure(
    service_name="backend",
    log_file="/logs/backend.log",
)

logger = LoggerFactory.get_logger(__name__)

logger.info(f"Starting app in {settings.environment} environment")

origins = [
    "http://localhost:3000",  # local React/Next.js dev
    "http://127.0.0.1:3000",  # local React/Next.js dev
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    await init_pool()
    logger.info("Database connection pool initialized")
    yield
    # Shutdown code
    await close_pool()
    logger.info("Database connection pool closed")


app = FastAPI(title="Lumina API's", docs_url="/", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(books_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all
    allow_credentials=True,  # needed if sending cookies/auth headers
    allow_methods=["*"],  # or restrict: ["GET", "POST"]
    allow_headers=["*"],  # or restrict to specific headers
)

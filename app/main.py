import structlog
from app.core.semantic import build_corpus_cache
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router, init_db
from app.core.loader import load_faq

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    entries = load_faq()
    build_corpus_cache(entries)
    log.info("app_startup_complete", faq_count=len(entries))
    yield
    log.info("app_shutdown")


app = FastAPI(
    title="WIU Library Chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router, prefix="/api")

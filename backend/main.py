import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ml import model_manager
from routers.api_routes import api_router
from routers.exploration_routes import explore_router
from routers.user_routes import user_router

# Suppress low-level library warnings (OpenMP/MKL)
os.environ["KMP_WARNINGS"] = "0"
os.environ["OMP_WARNINGS"] = "0"

if sys.platform != "win32":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")
    try:
        from multiprocessing import resource_tracker
        # Monkey-patch to suppress the "leaked semaphore" warning on exit
        resource_tracker._warn = lambda *args, **kwargs: None
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start model loading in the background when the server boots."""
    model_manager.start_background_init()
    yield


app = FastAPI(title="The Local Minima API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(explore_router)
app.include_router(user_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/status")
def get_system_status():
    """Returns the current model initialization status for the frontend boot sequence."""
    return model_manager.get_status()

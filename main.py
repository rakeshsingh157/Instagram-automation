from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
from api.routes_api import router as api_router
from api.routes_auth import router as auth_router
from api.routes_admin import router as admin_router
from api.routes_comments import router as comments_router
from api.routes_webhook import router as webhook_router
from services.scheduler import start_scheduler
import os

# Create DB tables safely
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"CRITICAL DB ERROR: {e}")
    # We continue so the server at least starts and can show the error via /ping or logs

# Ensure static directories exist
os.makedirs("generated_content", exist_ok=True)

app = FastAPI(title="Instagram Automation Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for video hosting
app.mount("/static", StaticFiles(directory="generated_content"), name="static")

# Include Routers
app.include_router(admin_router, tags=["Admin Dashboard"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(api_router, prefix="/api/v1", tags=["API"])
app.include_router(comments_router, prefix="/api/v1/comments", tags=["Comment Replies"])
app.include_router(webhook_router, prefix="/api/v1", tags=["Webhook - DM Auto Reply"])

@app.on_event("startup")
async def startup_event():
    # Start APScheduler on server boot
    start_scheduler()

@app.get("/ping")
async def ping():
    return {"status": "alive"}

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    # Detailed log for Render Console
    print(f"ERROR OCCURRED: {type(exc).__name__}: {str(exc)}")
    traceback.print_exc() 
    
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "error_type": type(exc).__name__,
            "detail": str(exc)
        }
    )


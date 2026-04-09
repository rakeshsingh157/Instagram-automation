from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.database import get_db
from sqlalchemy.orm import Session
from models.models import BotSettings, PostHistory
from core.security import verify_token, create_access_token
from core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_cookie_user(request: Request):
    token = request.cookies.get("access_token")
    if not token or not verify_token(token):
        return None
    return True

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_post(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    if username != settings.BOT_USERNAME or password != settings.BOT_PASSWORD:
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_302_FOUND)
        
    access_token = create_access_token(data={"sub": username})
    
    res = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    res.set_cookie(key="access_token", value=access_token, httponly=False)
    return res

@router.get("/logout")
async def logout():
    res = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    res.delete_cookie("access_token")
    return res

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not get_cookie_user(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
    cfg = db.query(BotSettings).first()
    logs = db.query(PostHistory).order_by(PostHistory.timestamp.desc()).limit(20).all()
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "config": cfg, "logs": logs}
    )

from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import init_db, add_feed, get_feeds, delete_feed, get_recent_rss_articles, get_last_updated, get_setting, set_setting, get_job_status, get_clien_articles
from scheduler import start_scheduler, update_feeds_job, update_rss_job, update_clien_job_standalone, update_job_settings
from logger_config import logger
from dotenv import load_dotenv
import uvicorn
import os
from datetime import datetime, timedelta

# Load keys from key.env
load_dotenv("key.env")
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234") # Default fallback

app = FastAPI(title="RSSy2")

# Create templates and static directory if they don't exist
for folder in ["templates", "static"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    logger.info("Application starting...")
    init_db()
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Application shutting down...")

def is_authenticated(request: Request):
    return request.cookies.get("admin_auth") == "true"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    authenticated = is_authenticated(request)
    articles = get_recent_rss_articles(hours=24)
    feeds = get_feeds()
    
    top_articles = [a for a in articles if a['is_top_selection']]
    other_articles = [a for a in articles if not a['is_top_selection']]
    
    last_updated = get_last_updated()
    clien_articles = get_clien_articles()
    
    if last_updated:
        try:
            dt = datetime.fromisoformat(last_updated)
            last_updated = (dt + timedelta(hours=9)).isoformat()
        except:
            pass
    
    # Get Settings
    auto_refresh = get_setting('auto_refresh', 'true') == 'true'
    refresh_interval = int(get_setting('refresh_interval', 120))

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "top_articles": top_articles,
        "other_articles": other_articles,
        "feeds": feeds,
        "last_updated": last_updated,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval,
        "clien_articles": clien_articles,
        "authenticated": authenticated
    })

@app.post("/verify_pin")
async def verify_pin(pin: str = Form(...)):
    if pin == ADMIN_PIN:
        response = JSONResponse(content={"status": "success"})
        response.set_cookie(key="admin_auth", value="true", httponly=True, max_age=3600*24) # 1 day session
        return response
    return JSONResponse(content={"status": "error", "message": "Invalid PIN"}, status_code=401)

@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_auth")
    return response

@app.post("/feeds")
async def create_feed(request: Request, url: str = Form(...), name: str = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        add_feed(url, name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/", status_code=303)

@app.post("/feeds/delete")
async def remove_feed(request: Request, feed_id: str = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    delete_feed(feed_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/refresh/rss")
async def refresh_rss(request: Request, background_tasks: BackgroundTasks):
    if not is_authenticated(request):
         raise HTTPException(status_code=401, detail="Unauthorized")
    background_tasks.add_task(update_rss_job)
    return RedirectResponse(url="/", status_code=303)

@app.post("/refresh/clien")
async def refresh_clien(request: Request, background_tasks: BackgroundTasks):
    if not is_authenticated(request):
         raise HTTPException(status_code=401, detail="Unauthorized")
    background_tasks.add_task(update_clien_job_standalone)
    return RedirectResponse(url="/", status_code=303)

@app.post("/refresh")
async def refresh_feeds(request: Request, background_tasks: BackgroundTasks):
    # Keep legacy /refresh but protect it
    if not is_authenticated(request):
         raise HTTPException(status_code=401, detail="Unauthorized")
    # Trigger update in background
    background_tasks.add_task(update_feeds_job)
    # Return immediately to let UI poll for status
    return RedirectResponse(url="/", status_code=303)

@app.get("/job_status")
async def check_job_status():
    status = get_job_status('current_refresh')
    if not status:
        return {"status": "idle"}
    return status

@app.post("/settings")
async def update_settings(request: Request, auto_refresh: str = Form(None), refresh_interval: int = Form(...)):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Checkbox sends 'on' if checked, else None
    is_auto_refresh = True if auto_refresh == 'on' else False
    
    set_setting('auto_refresh', 'true' if is_auto_refresh else 'false')
    set_setting('refresh_interval', refresh_interval)
    
    update_job_settings(is_auto_refresh, refresh_interval)
    
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)

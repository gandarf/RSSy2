from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import init_db, add_feed, get_feeds, delete_feed, get_recent_articles, get_last_updated, get_setting, set_setting
from scheduler import start_scheduler, update_feeds_job, update_job_settings
import uvicorn
import os

app = FastAPI(title="RSSy2")

# Create templates directory if it doesn't exist (handled by mkdir command, but good to be safe)
if not os.path.exists("templates"):
    os.makedirs("templates")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    articles = get_recent_articles(hours=24)
    feeds = get_feeds()
    
    top_articles = [a for a in articles if a['is_top_selection']]
    other_articles = [a for a in articles if not a['is_top_selection']]
    
    last_updated = get_last_updated()
    
    # Get Settings
    auto_refresh = get_setting('auto_refresh', 'true') == 'true'
    refresh_interval = int(get_setting('refresh_interval', 120))

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "top_articles": top_articles,
        "other_articles": other_articles,
        "feeds": feeds,
        "feeds": feeds,
        "last_updated": last_updated,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval
    })

@app.post("/feeds")
async def create_feed(url: str = Form(...), name: str = Form(...)):
    try:
        add_feed(url, name)
        # Trigger immediate update for the new feed (optional, but good UX)
        # For simplicity, we might just let the scheduler handle it or run it in background
        # But user might want to see it immediately.
        # Let's just redirect for now.
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url="/", status_code=303)

@app.post("/feeds/delete")
async def remove_feed(feed_id: str = Form(...)):
    delete_feed(feed_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/refresh")
async def refresh_feeds():
    # Run update job immediately
    # Note: This runs synchronously and might block. In production, use background tasks.
    # But for this simple app, it's okay or we can use BackgroundTasks
    update_feeds_job()
    return RedirectResponse(url="/", status_code=303)

@app.post("/settings")
async def update_settings(auto_refresh: str = Form(None), refresh_interval: int = Form(...)):
    # Checkbox sends 'on' if checked, else None
    is_auto_refresh = True if auto_refresh == 'on' else False
    
    set_setting('auto_refresh', 'true' if is_auto_refresh else 'false')
    set_setting('refresh_interval', refresh_interval)
    
    update_job_settings(is_auto_refresh, refresh_interval)
    
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)

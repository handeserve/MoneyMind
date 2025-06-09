# presentation_layer/main.py
from fastapi import FastAPI, HTTPException # Added HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import sqlite3 # For Connection type hint and errors
import logging # For logging within main.py as well

# Configure basic logging for this module if not already configured by uvicorn
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adjust path for get_sqlite_connection
from ..database.database import get_db_connection as get_sqlite_connection

# Import routers
from .routers import expenses_router, import_router, dashboard_router, settings_router, ai_router # Added ai_router

app = FastAPI(
    title="Personal Smart Expense Analyzer API",
    description="API for managing and analyzing personal expenses.",
    version="0.1.0",
    docs_url="/api/docs", 
    redoc_url="/api/redoc", 
    openapi_url="/api/v1/openapi.json"
)

# --- Database Dependency Setup ---
_main_py_dir = os.path.dirname(os.path.abspath(__file__))
_project_root_from_main = os.path.join(_main_py_dir, '..') 
DATABASE_FILE_PATH = os.path.join(_project_root_from_main, 'personal_expenses.db')

def get_db():
    db = get_sqlite_connection()
    if db is None:
        from ..database.database import DATABASE_PATH as ACTUAL_DB_PATH_USED
        logger.error(f"Failed to establish database connection via get_sqlite_connection. Expected path by database.py: {ACTUAL_DB_PATH_USED}")
        raise HTTPException(status_code=503, detail=f"Service Unavailable: Could not connect to the database. Path: {ACTUAL_DB_PATH_USED}")
    try:
        yield db
    finally:
        if db: 
            db.close()

# --- API Routers ---
# API routers should be included before generic frontend routes
app.include_router(expenses_router.router, prefix="/api/v1/expenses", tags=["Expenses Management"])
app.include_router(import_router.router, prefix="/api/v1/import", tags=["Data Import"])
app.include_router(dashboard_router.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(ai_router.router, prefix="/api/v1/ai", tags=["AI Processing"]) # Added AI router


# --- Static Files and Frontend Serving ---
# Path to the static files directory (presentation_layer/frontend/static)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "static")
logger.info(f"Static files directory calculated as: {STATIC_DIR}")

# Check if STATIC_DIR exists to help with debugging
if not os.path.exists(STATIC_DIR):
    logger.error(f"Static files directory NOT FOUND at: {STATIC_DIR}")
    logger.error("Please ensure the frontend/static directory and its contents are correctly placed.")
else:
    logger.info(f"Static files directory found at: {STATIC_DIR}. Mounting /static path.")
    # Mount static files directory. This makes /static/css/style.css etc. work.
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=FileResponse)
async def read_index():
    """Serves the main index.html page."""
    index_html_path = os.path.join(STATIC_DIR, "index.html")
    logger.debug(f"Attempting to serve index.html from: {index_html_path}")
    if not os.path.exists(index_html_path):
        logger.error(f"index.html not found at {index_html_path}")
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_html_path)

@app.get("/{page_name}.html", response_class=FileResponse)
async def read_html_page(page_name: str):
    """Serves other HTML pages like expenses.html."""
    html_file_path = os.path.join(STATIC_DIR, f"{page_name}.html")
    logger.debug(f"Attempting to serve HTML page: {html_file_path}")
    if not os.path.exists(html_file_path):
        logger.error(f"HTML page {page_name}.html not found at {html_file_path}")
        raise HTTPException(status_code=404, detail=f"{page_name}.html not found")
    return FileResponse(html_file_path)


if __name__ == "__main__":
    logger.info(f"Starting Uvicorn development server. Current CWD for main.py: {os.getcwd()}")
    from ..database.database import DATABASE_PATH as ACTUAL_DB_PATH_USED
    logger.info(f"Database file is expected to be managed by database.py at: {ACTUAL_DB_PATH_USED}")
    logger.info(f"Reference DATABASE_FILE_PATH in main.py is: {DATABASE_FILE_PATH}")
    
    if not os.path.normpath(ACTUAL_DB_PATH_USED) == os.path.normpath(DATABASE_FILE_PATH):
        logger.warning(f"Mismatch in database path calculation: main.py reference is {DATABASE_FILE_PATH}, but database.py uses {ACTUAL_DB_PATH_USED}")
    else:
        logger.info("Database path consistency check passed between main.py reference and database.py usage.")

    logger.info("Static files directory is configured to: " + STATIC_DIR)
    logger.info("Access the API docs at http://localhost:8000/api/docs")
    logger.info("Access the frontend at http://localhost:8000/")
    logger.info("Access expenses page at http://localhost:8000/expenses.html")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

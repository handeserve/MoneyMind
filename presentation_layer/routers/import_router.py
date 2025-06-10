import logging
import os
import shutil
import tempfile
from sqlite3 import Connection
import sqlite3

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Assuming get_db is in main.py, which is one level up from routers directory
from presentation_layer.dependencies import get_db

# Data importer function
from database import data_importer as importer
from database import csv_parser
from database import database as db_ops
from database.data_importer import import_data
from database.db import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

def save_upload_file(upload_file):
    suffix = "." + upload_file.filename.split(".")[-1] if "." in upload_file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(upload_file.file, temp_file)
        return temp_file.name

@router.post("/csv")
async def import_csv_file(
    file: UploadFile = File(...),
    channel: str = Form(...)
):
    """
    Import expense data from CSV file.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # 创建临时文件
    temp_file = None
    try:
        # 保存上传的文件到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            content = await file.read()
            temp.write(content)
            temp_file = temp.name
            logger.info(f"Uploaded CSV file saved temporarily to: {temp_file} for channel: {channel}")

        # 获取数据库连接
        db_conn = get_db_connection()
        
        # 导入数据
        summary = import_data(temp_file, channel, db_conn)
        
        return JSONResponse(content={
            "message": "Import completed",
            "summary": {
                "total": summary.total,
                "imported": summary.imported,
                "skipped": summary.skipped,
                "failed": summary.failed
            }
        })

    except Exception as e:
        logger.error(f"Error during file import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 清理临时文件
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
            logger.info(f"Temporary file {temp_file} deleted")

# Basic logging setup if this module is run directly (for testing, not typical)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("import_router.py loaded. This module is intended to be imported by main.py and run by Uvicorn.")

import logging
import os
import shutil
import tempfile
from sqlite3 import Connection
import sqlite3
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi import Depends
from pydantic import BaseModel

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

class ImportHistoryItem(BaseModel):
    filename: str
    channel: str
    import_time: str
    total_records: int
    successful_records: int
    failed_records: int
    status: str
    message: str

def save_upload_file(upload_file):
    suffix = "." + upload_file.filename.split(".")[-1] if "." in upload_file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(upload_file.file, temp_file)
        return temp_file.name

@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    channel: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Import expense data from CSV file.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    try:
        # 保存上传的文件
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        logger.info(f"Uploaded CSV file saved temporarily to: {temp_file.name} for channel: {channel}")

        # 导入数据
        result = import_data(temp_file.name, channel, db)
        
        return JSONResponse(content={
            "message": "Import completed",
            "summary": {
                "total": result.total,
                "imported": result.imported,
                "skipped": result.skipped,
                "failed": result.failed
            }
        })
    except Exception as e:
        logger.error(f"Error during file import: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 删除临时文件
        try:
            os.unlink(temp_file.name)
            logger.info(f"Temporary file {temp_file.name} deleted")
        except Exception as e:
            logger.error(f"Error deleting temporary file: {str(e)}")

@router.get("/history", response_model=List[ImportHistoryItem])
async def get_import_history(db: sqlite3.Connection = Depends(get_db_connection)):
    """
    获取导入历史记录
    """
    try:
        # 这里暂时返回模拟数据，实际应该从数据库查询
        # 如果有导入历史表的话可以从那里查询
        history = [
            {
                "filename": "alipay_export.csv",
                "channel": "Alipay",
                "import_time": "2024-06-10T10:30:00",
                "total_records": 360,
                "successful_records": 360,
                "failed_records": 0,
                "status": "success",
                "message": "导入成功"
            }
        ]
        return history
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Basic logging setup if this module is run directly (for testing, not typical)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("import_router.py loaded. This module is intended to be imported by main.py and run by Uvicorn.")

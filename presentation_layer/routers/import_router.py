import logging
import os
import shutil
import tempfile
from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

# Assuming get_db is in main.py, which is one level up from routers directory
from ..main import get_db

# Data importer function
from ...database.data_importer import import_data

router = APIRouter()

@router.post("/csv")
async def import_csv_file(
    db: Connection = Depends(get_db),
    channel: str = Form(..., description="The source channel of the CSV file (e.g., 'WeChat Pay', 'Alipay')."),
    file: UploadFile = File(..., description="The CSV file to import.")
):
    """
    Imports expense data from a CSV file (WeChat Pay or Alipay).
    The file is temporarily saved on the server for processing.
    """
    
    # Basic validation for channel
    supported_channels = ["WeChat Pay", "Alipay"] # Can be expanded or moved to config
    if channel not in supported_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported channel '{channel}'. Supported channels are: {', '.join(supported_channels)}."
        )

    # Ensure the uploaded file is a CSV (basic check by extension)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .csv files are allowed.")

    temp_file_path = None
    try:
        # Create a temporary file to store the uploaded CSV content
        # tempfile.NamedTemporaryFile creates a file that is deleted when closed.
        # We need to ensure it's written to, closed, and then passed to import_data.
        # Suffix is important for some OS/libraries.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        logging.info(f"Uploaded CSV file saved temporarily to: {temp_file_path} for channel: {channel}")

        # Call the data importer function
        # import_data expects db_connection, file_path, channel
        import_summary = import_data(db_connection=db, file_path=temp_file_path, channel=channel)
        
        logging.info(f"Import summary for {file.filename}: {import_summary}")
        
        # Check status from summary to determine HTTP response
        # This logic depends on the structure of import_summary (defined in data_importer.py)
        if import_summary.get('parse_errors', 0) > 0:
            # If parsing failed, it's likely a client-side error (bad file format)
            raise HTTPException(status_code=422, detail=f"File parsing failed: {import_summary.get('status_message', 'Unknown parsing error')}")
        
        if import_summary.get('successfully_imported', 0) == 0 and import_summary.get('total_records_in_file', 0) > 0 and import_summary.get('insert_errors',0) > 0 :
             # No records imported, but there were records and insert errors
             raise HTTPException(status_code=500, detail=f"Import process completed, but no records were imported due to database errors: {import_summary.get('status_message', 'Check logs')}")


        return {
            "filename": file.filename,
            "channel": channel,
            "import_summary": import_summary
        }

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logging.error(f"Error during CSV import for file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during CSV import: {str(e)}")
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logging.info(f"Temporary file {temp_file_path} deleted.")
            except Exception as e_remove:
                logging.error(f"Failed to delete temporary file {temp_file_path}: {e_remove}")
        
        # Ensure the uploaded file object is closed
        if file and hasattr(file, 'file') and not file.file.closed:
            file.file.close()

# Basic logging setup if this module is run directly (for testing, not typical)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("import_router.py loaded. This module is intended to be imported by main.py and run by Uvicorn.")

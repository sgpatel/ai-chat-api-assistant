# app/api/v1/endpoints/operations.py

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any

# Use absolute imports within the 'app' package
from app.core.api_parser import APISpecParser
from app.config import logger

# --- Dependency Function for Parser (from app state) ---
def get_api_parser(request: Request) -> APISpecParser:
    """Dependency to retrieve the APISpecParser instance."""
    logger.debug("Attempting to get API Parser from app state...") # Added Log
    parser = getattr(request.app.state, 'api_parser', None)
    if parser is None:
        logger.error("API Parser not found in app state during request.")
        # Log available state attributes for debugging
        logger.debug(f"Available attributes in app.state: {dir(request.app.state)}")
        raise HTTPException(status_code=500, detail="API Parser not available.")
    logger.debug("API Parser retrieved successfully from app state.") # Added Log
    return parser
# --- End Dependency Function ---


router = APIRouter()

# --- CHANGED ROUTE PATH from "/" to "" ---
@router.get("") # Register at /api/v1/operations (no trailing slash)
async def get_available_operations(
    parser: APISpecParser = Depends(get_api_parser)
) -> List[Dict[str, Any]]:
    """
    Lists available API operations based on the loaded specification.
    Includes summary/description if available.
    """
    logger.info("Request received for available API operations.")
    operations = []
    endpoints = parser.list_endpoints() # Assuming this returns list of (path, method) tuples

    for path, method in endpoints:
        # Get summary/description for better display
        # Handle potential None return from get_endpoint_info
        endpoint_info = parser.get_endpoint_info(path, method)
        summary = "N/A"
        op_id = f"{method}_{path.replace('/','_').strip('_')}" # Default op_id

        if endpoint_info:
            summary = endpoint_info.summary or f"{method.upper()} {path}"
            if endpoint_info.operation_id:
                op_id = endpoint_info.operation_id # Use operationId if available

        operations.append({
            "id": op_id, # A unique ID for selection
            "summary": summary, # User-friendly display name
            "path": path,
            "method": method
        })

    logger.info(f"Returning {len(operations)} available operations.")
    return operations


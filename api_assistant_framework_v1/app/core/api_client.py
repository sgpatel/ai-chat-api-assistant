# app/core/api_client.py

import asyncio
import httpx
from typing import Dict, Any, Optional, Tuple
import re # Import regex module for finding path params

# Use absolute imports within the 'app' package
from app.config import logger, settings

class APIClient:
    """Handles making calls to the target external APIs using httpx."""

    async def call_external_api(
        self,
        path: str,
        method: str,
        parameters: Dict[str, Any],
        # parameter_details: List[ParameterInfo] = [] # Still needed for robust location handling
    ) -> Tuple[int, Dict[str, Any]]:
        """Calls the external API, substituting path parameters."""
        method = method.upper()
        base_url = settings.TARGET_API_BASE_URL
        if not base_url:
            logger.error("TARGET_API_BASE_URL is not configured in settings/.env")
            return 500, {"detail": "Target API base URL is not configured."}

        processed_path = path
        # --- Simple Path Parameter Substitution ---
        # Create a copy to avoid modifying the original dict if needed elsewhere
        params_for_body_query = parameters.copy()
        # Find all placeholders like {param_name} in the path
        path_param_names = set(re.findall(r"\{(\w+)\}", path))

        logger.debug(f"Found potential path parameters in path '{path}': {path_param_names}")

        for name in path_param_names:
            if name in parameters:
                value_to_substitute = parameters[name]
                logger.debug(f"Substituting path parameter '{{{name}}}' with value '{value_to_substitute}'")
                processed_path = processed_path.replace(f"{{{name}}}", str(value_to_substitute))
                # Remove used path parameter from the dict intended for query/body
                params_for_body_query.pop(name, None)
            else:
                # This shouldn't happen if the flow engine collected all required path params
                logger.error(f"Path parameter '{{{name}}}' found in path but missing in provided parameters!")
                return 400, {"detail": f"Missing required path parameter: {name}"}
        # --- End Path Parameter Substitution ---

        if not processed_path.startswith('/'): processed_path = '/' + processed_path
        url = f"{base_url}{processed_path}" # Construct URL using processed path

        json_body: Optional[Dict[str, Any]] = None
        query_params: Optional[Dict[str, Any]] = None

        # Use the remaining parameters for query/body
        if method in ["POST", "PUT", "PATCH"]:
             json_body = params_for_body_query
        elif method == "GET":
             query_params = params_for_body_query
        # TODO: Refine this based on parameter_details.location

        # --- Define Headers ---
        headers = { "Content-Type": "application/json", "Accept": "application/json" }
        if settings.OPENAI_API_KEY: # Example using OpenAI key
            logger.debug("Adding OpenAI Authorization header.")
            headers["Authorization"] = f"Bearer {settings.OPENAI_API_KEY}"
            # headers["OpenAI-Beta"] = "assistants=v2" # Add if needed
        elif settings.MY_API_KEY: # Example using custom key
             logger.debug("Adding custom X-API-Key header.")
             headers["X-API-Key"] = settings.MY_API_KEY
        else: logger.debug("No specific API key found in settings.")
        # --- End Header Definition ---

        logger.info(f"Calling External API: {method} {url}")
        logger.debug(f"Query Params: {query_params}")
        logger.debug(f"JSON Body (keys): {list(json_body.keys()) if json_body else None}")
        logger.debug(f"Request Headers: {list(headers.keys())}")

        # --- REAL HTTP CALL LOGIC ---
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method, url=url, params=query_params,
                    json=json_body, headers=headers
                )
            # ... (rest of response handling logic as before) ...
            logger.info(f"External API Response Status: {response.status_code}")
            response_body = {}
            try:
                if response.status_code != 204:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' in content_type: response_body = response.json()
                    else: response_body = {"detail": f"Received status {response.status_code} with non-JSON content type: {content_type}", "raw_body": response.text}; logger.warning(f"Non-JSON response received...")
                logger.debug(f"External API Response Body (first 200 chars): {str(response_body)[:200]}...")
            except Exception as json_error:
                logger.warning(f"Could not decode API response as JSON. Status: {response.status_code}, Error: {json_error}, Body: {response.text[:100]}...")
                response_body = {"detail": f"Received status {response.status_code}. Response body could not be parsed.", "raw_body": response.text}
            return response.status_code, response_body

        except httpx.TimeoutException: logger.error(f"Timeout error calling {method} {url}"); return 504, {"detail": "Request timed out contacting the external API."}
        except httpx.RequestError as e: logger.error(f"Request error calling {method} {url}: {e}", exc_info=True); return 503, {"detail": f"Could not connect to the external API: {e}"}
        except Exception as e: logger.error(f"Unexpected error during API call to {method} {url}: {e}", exc_info=True); return 500, {"detail": f"An unexpected error occurred: {e}"}
        # --- END REAL HTTP CALL LOGIC ---


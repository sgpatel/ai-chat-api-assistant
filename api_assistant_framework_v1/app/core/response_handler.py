# app/core/response_handler.py
# Processes responses from APIClient and formats them for the chat UI.

import json
from typing import Dict, Any, Tuple

# Use absolute import within the 'app' package
from app.config import logger

class ResponseHandler:
    """
    Processes responses from the APIClient and formats them
    into user-understandable messages for the chat UI.
    """

    def format_api_response(
        self,
        api_response: Tuple[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Takes the status code and body from the API call and creates
        a message payload suitable for the chat frontend.

        Args:
            api_response: Tuple of (status_code, response_body_dict).

        Returns:
            A dictionary representing the message to send to the chat UI.
            Contains 'type' ('final_message', 'error_message') and 'text'.
        """
        status_code, body = api_response
        logger.info(f"Formatting API response: Status={status_code}")
        logger.debug(f"Raw response body (first 200 chars): {str(body)[:200]}")

        response_payload = {} # Start with empty dict

        try:
            if 200 <= status_code < 300:
                # --- Success Handling ---
                response_payload["type"] = "final_message"
                message = "" # Initialize message string

                if status_code == 204: # No Content
                    message = "✅ **Success!** Operation completed (No content returned)."
                elif isinstance(body, dict):
                    # Try to find a meaningful message field
                    message_text = body.get("message", body.get("detail", None))
                    if message_text:
                        message = f"✅ **Success:** {message_text}"
                    else:
                        # If no message field, format the JSON data
                        try:
                            summary = json.dumps(body, indent=2, ensure_ascii=False)
                            # Keep details tag for potentially large single JSON objects
                            if len(summary) > 700:
                                summary_display = f"<details><summary>Click to view JSON details</summary>\n\n```json\n{summary}\n```\n\n</details>"
                            else:
                                summary_display = f"```json\n{summary}\n```"
                            message = f"✅ **Success!**\n\n**Received Data:**\n{summary_display}"
                        except Exception as dump_error:
                            logger.error(f"Error formatting dictionary body as JSON: {dump_error}")
                            message = f"✅ **Success!** Received data (Could not format as JSON)."

                elif isinstance(body, list):
                    # --- REVISED List Handling ---
                    count = len(body)
                    message = f"✅ **Success!** Found **{count}** item(s)."
                    if count > 0:
                        try:
                            sample_count = 3 # Number of sample items to show
                            summary = json.dumps(body[:sample_count], indent=2, ensure_ascii=False)
                            summary_display = f"```json\n{summary}\n```"

                            # Add label and truncation note clearly
                            if count > sample_count:
                                message += f"\n\n**Sample Data (first {sample_count} items):**\n{summary_display}\n... ({count - sample_count} more items not shown)"
                            else:
                                # If showing all items (<= sample_count)
                                message += f"\n\n**Data ({count} item(s)):**\n{summary_display}"

                        except Exception as dump_error:
                            logger.error(f"Error formatting list body as JSON: {dump_error}")
                            message += f"\n(Could not format sample data as JSON)."
                    # No change if count is 0, initial message is sufficient
                    # --- END REVISED List Handling ---

                else:
                    # Handle other successful response types
                    raw_body = body.get("raw_body", str(body))
                    if len(raw_body) > 700: raw_body = raw_body[:700] + "\n... (truncated)"
                    message = f"✅ **Success!** ({status_code}).\n\n**Response:**\n```\n{raw_body}\n```"

                response_payload["text"] = message

            else:
                # --- Error Handling (Keep as before) ---
                response_payload["type"] = "error_message"
                error_detail = "An unknown error occurred."
                if isinstance(body, dict):
                    error_detail = body.get("detail", body.get("message", body.get("error", error_detail)))
                    raw_body_info = body.get("raw_body")
                    if raw_body_info and error_detail == "An unknown error occurred.": error_detail = f"Non-JSON response received. Body: {raw_body_info[:200]}"
                    elif error_detail == "An unknown error occurred.":
                         try:
                             error_body_summary = json.dumps(body, indent=2);
                             if len(error_body_summary) > 500: error_body_summary = error_body_summary[:500] + "\n...(truncated)"
                             error_detail += f"\n```json\n{error_body_summary}\n```"
                         except: error_detail += f" Body: {str(body)[:200]}"
                elif isinstance(body, str): error_detail = body[:500]
                response_payload["text"] = f"⚠️ **Error ({status_code}):** {error_detail}"

        except Exception as e:
            logger.error(f"Error formatting API response: {e}", exc_info=True)
            response_payload["type"] = "error_message"
            response_payload["text"] = f"⚠️ **Internal Error:** Could not process the API response (Status: {status_code})."

        logger.info(f"Formatted response payload type: {response_payload.get('type')}")
        return response_payload


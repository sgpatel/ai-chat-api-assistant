# app/api/v1/endpoints/chat.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Tuple

# Import engine, state manager, and state model
from app.core.flow_engine import DialogFlowEngine
from app.core.state_manager import StateManager
from app.models.conversation_state import ConversationState
from app.config import logger # Import logger

# Dependency Function for Engine (from app state)
def get_dialog_engine(request: Request) -> DialogFlowEngine:
    """Dependency to retrieve the DialogFlowEngine instance from app state."""
    engine = getattr(request.app.state, 'dialog_engine', None)
    if engine is None:
        logger.error("Dialog Engine not found in app state during request.")
        raise HTTPException(status_code=500, detail="Chat engine is not available.")
    return engine

router = APIRouter()

class UserInput(BaseModel):
    """Model for incoming messages from the chat frontend."""
    user_id: str
    type: str # 'intent' or 'parameter_response'
    intent_string: Optional[str] = None
    target_api_path: Optional[str] = None
    target_api_method: Optional[str] = None
    parameter_name: Optional[str] = None
    parameter_value: Any = None


@router.post("/message")
async def handle_chat_message(
    user_input: UserInput,
    # Inject state manager (will create instance with DB session per request)
    state_manager: StateManager = Depends(StateManager),
    # Inject the singleton dialog engine instance
    dialog_engine: DialogFlowEngine = Depends(get_dialog_engine)
) -> Dict[str, Any]:
    """
    Handles incoming chat messages, loads/saves state using StateManager,
    processes logic using DialogFlowEngine, and returns the next response.
    """
    # --- ADDED ENTRY LOG ---
    logger.info(f"--- Entered handle_chat_message for user {user_input.user_id}, type: {user_input.type} ---")
    # --- END ADDED ENTRY LOG ---

    logger.info(f"Received chat message from user {user_input.user_id}: type={user_input.type}") # Keep original log too

    response_payload: Optional[Dict[str, Any]] = None
    state: Optional[ConversationState] = None # Ensure state is defined

    try:
        # 1. Load conversation state for the user
        logger.debug(f"Loading state for user {user_input.user_id}...")
        state = await state_manager.load_state(user_input.user_id)
        logger.debug(f"State loaded for user {user_input.user_id}.")

        # 2. Process input using the dialog engine, passing the loaded state
        if user_input.type == 'intent':
            if not user_input.intent_string or not user_input.target_api_path or not user_input.target_api_method:
                raise HTTPException(status_code=400, detail="Missing fields for intent message type.")

            target_details = (user_input.target_api_path, user_input.target_api_method)
            logger.debug(f"Calling process_intent for user {user_input.user_id}...")
            response_payload = await dialog_engine.process_intent( # This is sync
                state=state,
                intent=user_input.intent_string,
                target_api_details=target_details
            )
            logger.debug(f"process_intent completed for user {user_input.user_id}.")

        elif user_input.type == 'parameter_response':
            if not user_input.parameter_name or user_input.parameter_value is None:
                    raise HTTPException(status_code=400, detail="Missing fields for parameter_response message type.")

            logger.debug(f"Calling process_response for user {user_input.user_id}, param: {user_input.parameter_name}...")
            response_payload = await dialog_engine.process_response( # This is async
                state=state,
                parameter_name=user_input.parameter_name,
                value=user_input.parameter_value
            )
            logger.debug(f"process_response completed for user {user_input.user_id}.")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid message type: {user_input.type}")

        # 3. Save the potentially modified state (important!)
        logger.debug(f"Saving state for user {user_input.user_id}...")
        await state_manager.save_state(state)
        logger.debug(f"State saved for user {user_input.user_id}.")

        # 4. Handle engine response
        if response_payload is None:
                logger.warning(f"Dialog engine returned None for user {user_input.user_id}")
                response_payload = {"type": "error_message", "text": "I'm not sure how to proceed from here."}

        logger.info(f"--- Exiting handle_chat_message for user {user_input.user_id} ---")
        return response_payload

    except Exception as e:
        logger.error(f"Error processing chat message for user {user_input.user_id}: {e}", exc_info=True)
        # Attempt to save state even if processing failed, might contain error info
        if state:
            try:
                    state.error_message = f"Processing Error: {e}"
                    await state_manager.save_state(state)
            except Exception as save_err:
                    logger.error(f"Failed to save error state for user {user_input.user_id}: {save_err}")

        # Return a generic error message to the frontend
        # Raise HTTPException here so FastAPI returns proper 500, or return JSON directly
        # raise HTTPException(status_code=500, detail="Internal server error processing message.")
        return {"type": "error_message", "text": "Sorry, an unexpected error occurred."} # Returning JSON directly


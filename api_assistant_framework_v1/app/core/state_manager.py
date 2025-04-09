# app/core/state_manager.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db_session
from app.db import crud as db_crud
from app.models.conversation_state import ConversationState
from app.config import logger

class StateManager:
    """Handles loading and saving conversation state using the database."""

    # Inject the DB session using FastAPI's dependency system
    # Note: This means StateManager instances are created per-request
    # If performance is critical, session could be passed to methods instead.
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        self.db = db

    async def load_state(self, user_id: str) -> ConversationState:
        """Loads state for a user, creating a new one if not found."""
        state = await db_crud.get_conversation_state(self.db, user_id)
        if state is None:
            logger.info(f"No existing state found for user {user_id}, creating new.")
            state = ConversationState(user_id=user_id)
            # No need to save immediately, will be saved after processing
        else:
             logger.info(f"Loaded existing state for user {user_id}.")
        return state

    async def save_state(self, state: ConversationState):
        """Saves the current state to the database."""
        await db_crud.save_conversation_state(self.db, state)
        # Commit happens in get_db_session context manager

    async def delete_state(self, user_id: str):
        """Deletes state for a user."""
        await db_crud.delete_conversation_state(self.db, user_id)


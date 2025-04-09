# app/db/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Optional

from app.db.models import ConversationStateDB
from app.models.conversation_state import ConversationState as ConversationStatePydantic
from app.config import logger
import datetime
import json # To handle potential serialization issues if needed

async def get_conversation_state(db: AsyncSession, user_id: str) -> Optional[ConversationStatePydantic]:
    """Retrieves conversation state for a user from the database."""
    logger.debug(f"Attempting to load state for user_id: {user_id}")
    result = await db.execute(
        select(ConversationStateDB).filter(ConversationStateDB.user_id == user_id)
    )
    db_state = result.scalars().first()
    if db_state:
        logger.debug(f"State found for user_id: {user_id}")
        try:
            # Convert DB model -> Pydantic model using ORM mode (from_attributes)
            pydantic_state = ConversationStatePydantic.model_validate(db_state)
            return pydantic_state
        except Exception as e:
             logger.error(f"Failed to validate DB state into Pydantic model for user {user_id}: {e}", exc_info=True)
             return None
    else:
        logger.debug(f"No state found for user_id: {user_id}")
        return None

async def save_conversation_state(db: AsyncSession, state: ConversationStatePydantic):
    """Creates or updates conversation state in the database."""
    logger.debug(f"Attempting to save state for user_id: {state.user_id}")
    existing_state = await db.get(ConversationStateDB, state.user_id)

    state_data = state.model_dump(mode='json')
    # Remove keys that are not columns in ConversationStateDB or handled separately
    state_data.pop('user_id', None) # Handled as PK
    # --- ADD THIS LINE to remove conversation_id ---
    state_data.pop('conversation_id', None) # Not a DB column
    # --- END ADDED LINE ---

    # Ensure last_update_time is set correctly for DB save
    state_data['last_update_time'] = datetime.datetime.utcnow()

    if existing_state:
        logger.debug(f"Updating existing state for user_id: {state.user_id}")
        stmt = (
            update(ConversationStateDB)
            .where(ConversationStateDB.user_id == state.user_id)
            .values(**state_data)
        )
        await db.execute(stmt)
    else:
        logger.debug(f"Creating new state for user_id: {state.user_id}")
        # Pass user_id separately, and the rest via state_data
        db_state = ConversationStateDB(user_id=state.user_id, **state_data)
        db.add(db_state)

    # Commit is handled by the get_db_session dependency's context manager
    logger.debug(f"State save operation prepared for user_id: {state.user_id}")

async def delete_conversation_state(db: AsyncSession, user_id: str):
    """Deletes conversation state for a user."""
    logger.debug(f"Attempting to delete state for user_id: {user_id}")
    stmt = delete(ConversationStateDB).where(ConversationStateDB.user_id == user_id)
    await db.execute(stmt)
    logger.debug(f"State delete operation prepared for user_id: {user_id}") # Commit handled by context manager


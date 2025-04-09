# app/db/models.py

import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID # Use specific UUID for Postgres if needed
from app.db.database import Base

class ConversationStateDB(Base):
    """SQLAlchemy model for storing conversation state."""
    __tablename__ = "conversation_states"

    # Use user_id as primary key, assuming it's unique per conversation context
    user_id = Column(String, primary_key=True, index=True)

    # Store relevant fields from Pydantic ConversationState model
    target_endpoint_path = Column(String, nullable=True)
    target_endpoint_method = Column(String, nullable=True)

    # Use JSON type for dictionary and list fields
    # Note: JSON support might require specific handling or libraries depending on the DB backend
    collected_parameters = Column(JSON, default={})
    required_parameters_list = Column(JSON, default=[])
    asked_parameter_names = Column(JSON, default=[])

    next_parameter_name = Column(String, nullable=True)

    # Store last messages as JSON or Text
    last_assistant_message = Column(JSON, nullable=True) # Store the instruction/message structure
    last_user_message = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)

    last_update_time = Column(
        DateTime(timezone=False), # SQLite doesn't natively support timezone=True
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow # Automatically update timestamp
    )

# app/ui_generators/chat_elements.py
# Defines the structure for instructing the frontend chat UI.

from pydantic import BaseModel
from typing import Dict, Any, Optional, List # Ensure List is imported if used

class ChatUIInstructionData(BaseModel):
    """
    Defines the structure for instructing the frontend chat UI
    on what prompt and interactive component to display.
    """
    prompt: str # The text prompt/question for the user
    ui_component: Dict[str, Any] # Description of the UI element needed

    # Example ui_component structures expected by frontend:
    # {'type': 'text_input', 'parameter_name': 'task_name', 'placeholder': '...', 'description': '...', 'default': '...'}
    # {'type': 'dropdown', 'parameter_name': 'status', 'options': ['Pending', ...], 'description': '...', 'default': '...'}
    # {'type': 'date_picker', 'parameter_name': 'due_date', 'description': '...'}
    # {'type': 'number_input', 'parameter_name': 'priority', 'description': '...'}
    # {'type': 'checkbox', 'parameter_name': 'send_notification', 'description': '...', 'default': True}
    # {'type': 'multi_select', 'parameter_name': 'assignees', 'item_type': 'string', 'description': '...'}
    # {'type': 'json_input', 'parameter_name': 'metadata', 'description': '...'}
    # etc.


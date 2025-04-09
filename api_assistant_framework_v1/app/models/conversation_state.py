# app/models/conversation_state.py

from pydantic import BaseModel, Field, ConfigDict # Import ConfigDict
from typing import Dict, Any, Optional, List
import datetime
import uuid

# Import EndpointInfo for type hinting
from .api_spec import EndpointInfo

class ConversationState(BaseModel):
    """Pydantic model representing the state of a single user's conversation flow."""
    # Use model_config for Pydantic V2 ORM mode
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str # Identifier for the user (PK in DB)

    target_endpoint_path: Optional[str] = None
    target_endpoint_method: Optional[str] = None

    collected_parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters_list: List[str] = Field(default_factory=list)
    asked_parameter_names: List[str] = Field(default_factory=list)
    next_parameter_name: Optional[str] = None

    last_update_time: Optional[datetime.datetime] = None # Allow None, DB sets default/update
    error_message: Optional[str] = None
    last_assistant_message: Optional[Any] = None
    last_user_message: Optional[str] = None

    # --- Methods to manage state ---
    # These methods now operate on the instance, assuming it's loaded/saved externally

    def set_endpoint_details(self, endpoint_info: 'EndpointInfo'): # Use forward reference
        """Sets target endpoint details and resets parameters."""
        self.target_endpoint_path = endpoint_info.path
        self.target_endpoint_method = endpoint_info.method
        self.required_parameters_list = [
            p.name for p in endpoint_info.parameters if p.required
        ]
        self.collected_parameters = {}
        self.asked_parameter_names = []
        self.next_parameter_name = self._find_next_missing_required_param()
        # self.last_update_time = datetime.datetime.now() # Let DB handle this

    def add_collected_parameter(self, name: str, value: Any):
        """Adds a parameter value and determines the next needed parameter."""
        # TODO: Add validation logic here based on parameter schema
        self.collected_parameters[name] = value
        if name not in self.asked_parameter_names:
            self.asked_parameter_names.append(name)
        self.next_parameter_name = self._find_next_missing_required_param()
        # self.last_update_time = datetime.datetime.now() # Let DB handle this

    def get_next_parameter_to_ask(self) -> Optional[str]:
        """Gets the name of the next parameter needed."""
        # Ensure next_parameter_name is recalculated if needed
        if not self.next_parameter_name and not self.all_required_parameters_collected():
             self.next_parameter_name = self._find_next_missing_required_param()
        return self.next_parameter_name

    def _find_next_missing_required_param(self) -> Optional[str]:
        """Finds the first required parameter that hasn't been collected."""
        for param_name in self.required_parameters_list:
            if param_name not in self.collected_parameters:
                return param_name
        return None

    def all_required_parameters_collected(self) -> bool:
        """Checks if all required parameters have values."""
        return self._find_next_missing_required_param() is None

    def update_last_messages(self, assistant_msg: Optional[Any] = None, user_msg: Optional[str] = None):
        """Updates last message fields."""
        if assistant_msg is not None: # Allow clearing with None
            self.last_assistant_message = assistant_msg
        if user_msg is not None:
            self.last_user_message = user_msg
        # self.last_update_time = datetime.datetime.now() # Let DB handle this


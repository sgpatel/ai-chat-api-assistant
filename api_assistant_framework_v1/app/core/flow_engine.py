# app/core/flow_engine.py

import json # Make sure json is imported
from typing import Dict, Any, Optional, Tuple

# Import Pydantic models
from app.models.conversation_state import ConversationState
from app.models.api_spec import EndpointInfo, ParameterInfo
from app.ui_generators.chat_elements import ChatUIInstructionData

# Import other core components
from app.core.api_parser import APISpecParser
from app.core.api_client import APIClient
from app.core.response_handler import ResponseHandler
from app.config import logger

class DialogFlowEngine:
    """
    Orchestrates the conversation flow.
    Operates on a ConversationState object passed to its methods.
    """
    def __init__(self, api_parser: APISpecParser):
        self.api_parser = api_parser
        self.api_client = APIClient()
        self.response_handler = ResponseHandler()
        logger.info("DialogFlowEngine initialized.")

    # --- process_intent (Keep as before) ---
    async def process_intent(
        self,
        state: ConversationState,
        intent: str,
        target_api_details: Tuple[str, str]
    ) -> Optional[Dict[str, Any]]:
        state.update_last_messages(user_msg=intent)
        logger.info(f"Processing intent '{intent}' for user {state.user_id}, target: {target_api_details}")
        endpoint_info: Optional[EndpointInfo] = self.api_parser.get_endpoint_info(target_api_details[0], target_api_details[1])
        if not endpoint_info:
            error_msg = f"Sorry, I don't know how to '{intent}' (Endpoint {target_api_details} not found)."
            logger.error(f"Endpoint info not found for {target_api_details}")
            state.error_message = error_msg
            return {"type": "error_message", "text": error_msg}
        state.set_endpoint_details(endpoint_info)
        logger.info(f"State updated for {intent}. Required params: {state.required_parameters_list}") # Check this log!
        instruction = self._get_next_instruction(state, endpoint_info)
        if instruction:
             return {"type": "ui_instruction", "data": instruction.model_dump()}
        else:
             logger.warning("No required parameters found for intent. Flow needs enhancement.")
             return await self._trigger_api_call(state)
             #return {"type": "error_message", "text": "This action doesn't seem to require any parameters. (Functionality to proceed not fully implemented)."}


    # --- process_response (Keep as before) ---
    async def process_response(
        self,
        state: ConversationState,
        parameter_name: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        state.update_last_messages(user_msg=str(value))
        logger.info(f"Processing response for param '{parameter_name}' = '{str(value)[:100]}...' for user {state.user_id}")

        # Attempt to parse if it looks like JSON
        if isinstance(value, str):
            maybe_json_str = value.strip()
            if (maybe_json_str.startswith('[') and maybe_json_str.endswith(']')) or \
               (maybe_json_str.startswith('{') and maybe_json_str.endswith('}')):
                try: value = json.loads(maybe_json_str); logger.debug(f"Successfully parsed '{parameter_name}' as JSON.")
                except json.JSONDecodeError: logger.warning(f"Value for '{parameter_name}' looked like JSON but failed to parse. Sending as string.")

        state.add_collected_parameter(parameter_name, value)
        logger.debug(f"Collected params keys for user {state.user_id}: {list(state.collected_parameters.keys())}")

        if not state.target_endpoint_path or not state.target_endpoint_method:
             error_msg = "Internal error: Lost track of API goal state."; logger.error(f"Missing target endpoint in state for user {state.user_id}"); state.error_message = error_msg; return {"type": "error_message", "text": error_msg}

        endpoint_info: Optional[EndpointInfo] = self.api_parser.get_endpoint_info(state.target_endpoint_path, state.target_endpoint_method)
        if not endpoint_info:
             error_msg = "Internal error: Could not reload API goal details."; logger.error(f"Could not reload endpoint info for {state.target_endpoint_path} {state.target_endpoint_method}"); state.error_message = error_msg; return {"type": "error_message", "text": error_msg}

        if state.all_required_parameters_collected():
            logger.info(f"All required parameters collected for user {state.user_id}. Triggering API call.")
            return await self._trigger_api_call(state)
        else:
            instruction = self._get_next_instruction(state, endpoint_info)
            if instruction:
                return {"type": "ui_instruction", "data": instruction.model_dump()}
            else:
                 error_msg = "Internal error: Could not determine next step."; logger.error(f"Inconsistent state for user {state.user_id}: Not all params collected, but no next instruction."); state.error_message = error_msg; return {"type": "error_message", "text": error_msg}


    # --- _trigger_api_call (UPDATED with logging) ---
    async def _trigger_api_call(self, state: ConversationState) -> Dict[str, Any]:
         """Internal method to call the API and handle the response."""
         api_params = state.collected_parameters
         # --- ADD DEBUG LOG HERE ---
         logger.debug(f"Parameters prepared for APIClient for user {state.user_id}: {api_params}")
         # --- END DEBUG LOG ---
         try:
             if not state.target_endpoint_path or not state.target_endpoint_method:
                  logger.error(f"Cannot trigger API call: Missing endpoint path/method in state for user {state.user_id}")
                  return {"type": "error_message", "text": "Internal error: Cannot determine which API to call."}

             api_response_tuple = await self.api_client.call_external_api(
                 path=state.target_endpoint_path,
                 method=state.target_endpoint_method,
                 parameters=api_params # Pass collected params
             )
             formatted_response = self.response_handler.format_api_response(api_response_tuple)
             state.update_last_messages(assistant_msg=formatted_response)
             return formatted_response
         except Exception as e:
             logger.error(f"Error during API call or response handling for user {state.user_id}: {e}", exc_info=True)
             state.error_message = f"Failed to execute the API call: {e}"
             return {"type": "error_message", "text": "Sorry, I couldn't complete the request due to an internal error."}


    # --- _get_next_instruction (Keep as before) ---
    def _get_next_instruction(self, state: ConversationState, endpoint_info: EndpointInfo) -> Optional[ChatUIInstructionData]:
        next_param_name = state.get_next_parameter_to_ask()
        if not next_param_name: logger.debug("No next parameter needed."); return None
        param_info: Optional[ParameterInfo] = next((p for p in endpoint_info.parameters if p.name == next_param_name), None)
        if not param_info: logger.error(f"Could not find schema details for parameter '{next_param_name}'."); state.error_message = f"Internal error: parameter '{next_param_name}' details missing."; return None
        prompt = f"Please provide the {param_info.name.replace('_', ' ')}"
        if param_info.description: prompt += f" ({param_info.description})"
        prompt += ":"
        ui_component_details = self._map_schema_to_ui(param_info)
        instruction_data = ChatUIInstructionData(prompt=prompt, ui_component=ui_component_details)
        logger.info(f"Generated next instruction for user {state.user_id}: Ask for '{next_param_name}' using '{ui_component_details.get('type')}'")
        return instruction_data


    # --- _map_schema_to_ui (Keep as before) ---
    def _map_schema_to_ui(self, param_info: ParameterInfo) -> Dict[str, Any]:
        # (Implementation remains the same - maps array->json_input/tags_input etc.)
        schema = param_info.schema_details
        ui_info = {"parameter_name": param_info.name}
        if schema.enum: ui_info['type'] = 'dropdown'; ui_info['options'] = schema.enum
        elif schema.type == 'string':
            if schema.format == 'date': ui_info['type'] = 'date_picker'
            elif schema.format == 'date-time': ui_info['type'] = 'datetime_picker'
            else: ui_info['type'] = 'text_input'
        elif schema.type in ['integer', 'number']: ui_info['type'] = 'number_input'
        elif schema.type == 'boolean': ui_info['type'] = 'checkbox'
        elif schema.type == 'array':
            items_schema = schema.items if schema.items else {}; item_type = items_schema.get('type')
            if item_type == 'object': ui_info['type'] = 'json_input'; logger.debug(f"Mapping array of objects '{param_info.name}' to json_input")
            elif item_type: ui_info['type'] = 'tags_input'; ui_info['item_type'] = item_type; logger.debug(f"Mapping array of {item_type} '{param_info.name}' to tags_input")
            else: ui_info['type'] = 'json_input'; logger.warning(f"Array '{param_info.name}' has no item type specified, defaulting to json_input.")
        elif schema.type == 'object': ui_info['type'] = 'json_input'; logger.debug(f"Mapping object '{param_info.name}' to json_input")
        else: ui_info['type'] = 'text_input'
        if param_info.description: ui_info['description'] = param_info.description
        if schema.default is not None: ui_info['default'] = schema.default
        return ui_info


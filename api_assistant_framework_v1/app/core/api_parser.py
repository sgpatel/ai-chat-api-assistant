# app/core/api_parser.py
# Parses OpenAPI specifications (v2 & v3) to extract endpoint details.

import yaml
import json
from typing import Dict, Any, List, Optional, Tuple

# Use absolute imports within the 'app' package
from app.models.api_spec import ParameterSchema, ParameterInfo, EndpointInfo
from app.config import logger, settings # Use settings for spec file path

class APISpecParser:
    """
    Parses an OpenAPI specification (v2.0 or v3.x) (YAML or JSON) to extract
    endpoint and parameter information relevant for the chat assistant.
    """
    def __init__(self, spec_path: str = settings.API_SPEC_FILE):
        self.spec_path = spec_path
        self.spec_version = None # To store detected version (e.g., '2.0', '3.0')
        self.spec = self._load_and_validate_spec()
        if not self.spec:
            logger.critical(f"Parser initialization failed: Could not load/validate spec from {self.spec_path}.")
            raise ValueError(f"Failed to load/parse/validate API spec: {spec_path}")

        api_title = self.spec.get('info', {}).get('title', 'N/A')
        api_version = self.spec.get('info', {}).get('version', 'N/A')
        spec_v = self.spec.get('openapi') or self.spec.get('swagger')
        logger.info(f"Successfully loaded API Spec: {api_title} v{api_version} (Spec Version: {spec_v})")


    def _load_and_validate_spec(self) -> Optional[Dict[str, Any]]:
        """Loads and performs basic validation on the spec."""
        logger.info(f"Attempting to load API spec from: {self.spec_path}")
        spec_dict = None
        try:
            with open(self.spec_path, 'r', encoding='utf-8') as f:
                if self.spec_path.endswith(('.yaml', '.yml')):
                    spec_dict = yaml.safe_load(f)
                elif self.spec_path.endswith('.json'):
                    spec_dict = json.load(f)
                else:
                    # Attempt to guess (simple check)
                    content = f.read()
                    try: spec_dict = json.loads(content)
                    except json.JSONDecodeError:
                        try: f.seek(0); spec_dict = yaml.safe_load(f)
                        except yaml.YAMLError: pass # Handled below

            if spec_dict is None:
                 logger.error(f"Could not parse {self.spec_path} as JSON or YAML.")
                 return None

            # Basic Structure Validation for v2 or v3
            if 'openapi' in spec_dict and isinstance(spec_dict['openapi'], str) and spec_dict['openapi'].startswith('3.'):
                self.spec_version = '3.0' # Treat all 3.x as 3.0 for parsing logic
                if 'paths' in spec_dict and 'info' in spec_dict: return spec_dict
            elif 'swagger' in spec_dict and spec_dict['swagger'] == '2.0':
                self.spec_version = '2.0'
                if 'paths' in spec_dict and 'info' in spec_dict: return spec_dict

            # If neither matches known structures
            logger.error("Loaded specification does not appear to be a valid OpenAPI v3 or Swagger v2 document.")
            raise ValueError("Invalid OpenAPI/Swagger document structure.")

        except FileNotFoundError:
            logger.error(f"Specification file not found at {self.spec_path}")
            return None
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing specification file {self.spec_path}: {e}")
            return None
        except ValueError as e: # Catch validation error from above
             logger.error(f"Spec validation failed: {e}")
             raise # Re-raise validation error
        except Exception as e:
            logger.error(f"An unexpected error occurred loading spec {self.spec_path}: {e}", exc_info=True)
            return None

    def list_endpoints(self) -> List[Tuple[str, str]]:
        """Returns a list of available endpoints (path, method)."""
        endpoints = []
        if not self.spec or 'paths' not in self.spec:
            logger.warning("No paths found in API specification.")
            return []
        for path, methods in self.spec['paths'].items():
            for method_key in methods.keys():
                 method = method_key.lower()
                 if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace']:
                    endpoints.append((path, method))
        logger.debug(f"Found endpoints: {endpoints}")
        return endpoints

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """Simple local $ref resolver (components/schemas or definitions)."""
        logger.debug(f"Attempting to resolve $ref: {ref}")
        if not ref.startswith('#/'):
            logger.warning(f"Cannot resolve non-local or complex $ref: {ref}")
            return {}

        # Determine base path for refs based on spec version
        if self.spec_version == '2.0':
            base_ref_path = 'definitions'
        elif self.spec_version == '3.0':
            base_ref_path = 'components/schemas'
        else: # Should not happen if validation passed
            logger.error(f"Cannot resolve $ref, unknown spec version: {self.spec_version}")
            return {}

        full_ref_path = f"#/{base_ref_path}/"
        if not ref.startswith(full_ref_path):
             # Handle other potential ref types if necessary (e.g., parameters, responses)
             # For now, focus on schema refs
             logger.warning(f"Cannot resolve $ref outside '{base_ref_path}': {ref}")
             return {}

        schema_name = ref[len(full_ref_path):]
        definitions = self.spec.get(base_ref_path.split('/')[0], {}).get(base_ref_path.split('/')[1], {}) if '/' in base_ref_path else self.spec.get(base_ref_path, {})

        resolved_schema = definitions.get(schema_name, {})

        if resolved_schema:
            logger.debug(f"Successfully resolved $ref '{ref}' to schema '{schema_name}'")
            return resolved_schema if isinstance(resolved_schema, dict) else {}
        else:
            logger.warning(f"Could not resolve $ref: {ref}")
            return {}


    def _extract_schema_details(self, schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts relevant fields for ParameterSchema from a potentially resolved schema dictionary.
        Infers type if not explicitly present. Resolves $ref if present at this level.
        """
        if not isinstance(schema_dict, dict):
            logger.warning(f"Cannot extract details from non-dict schema: {type(schema_dict)}")
            return {"type": "string"} # Fallback

        # Resolve $ref if present at this property level
        if '$ref' in schema_dict:
            schema_dict = self._resolve_ref(schema_dict['$ref'])
            if not schema_dict: # If ref resolution failed
                return {"type": "string", "description": "Failed to resolve reference"}

        details = {}
        # Determine type
        if 'type' in schema_dict:
            details['type'] = schema_dict['type']
        elif 'properties' in schema_dict:
            details['type'] = 'object'
        elif 'items' in schema_dict:
            details['type'] = 'array'
        elif 'allOf' in schema_dict or 'oneOf' in schema_dict or 'anyOf' in schema_dict:
             # Composite types - treat as object for simplicity for now
             # Real handling would require merging/choosing properties
             details['type'] = 'object'
             logger.debug("Treating composite schema (allOf/oneOf/anyOf) as 'object' type for ParameterSchema.")
        elif 'enum' in schema_dict:
             # If only enum is present, infer type based on first enum value
             first_enum = schema_dict['enum'][0] if schema_dict['enum'] else None
             if isinstance(first_enum, bool): details['type'] = 'boolean'
             elif isinstance(first_enum, int): details['type'] = 'integer'
             elif isinstance(first_enum, float): details['type'] = 'number'
             else: details['type'] = 'string' # Default for enum
             logger.debug(f"Inferred type '{details['type']}' from enum.")
        else:
            # Default type if none found (e.g., just description)
            details['type'] = 'string' # Default to string
            logger.warning(f"Schema missing 'type', defaulting to 'string'. Schema keys: {list(schema_dict.keys())}")

        # Extract other common fields
        for key in ['description', 'format', 'enum', 'default', 'items', 'properties', 'additionalProperties']:
            if key in schema_dict:
                details[key] = schema_dict[key]

        return details

    def _process_schema_properties(self, schema: Dict[str, Any], location_prefix: str) -> Tuple[List[ParameterInfo], set]:
        """Helper to process properties from an object schema (or merged allOf)."""
        parameters: List[ParameterInfo] = []
        processed_prop_names = set()
        properties_to_process = schema.get('properties', {})
        required_fields_set = set(schema.get('required', []))
        logger.debug(f"[{location_prefix}] Processing properties: {list(properties_to_process.keys())}")
        logger.debug(f"[{location_prefix}] Required fields: {required_fields_set}")

        for name, prop_schema_dict in properties_to_process.items():
            if name in processed_prop_names: continue
            try:
                extracted_details = self._extract_schema_details(prop_schema_dict)
                param_schema = ParameterSchema.model_validate(extracted_details)

                is_required = name in required_fields_set
                # Use description from original prop_schema_dict if extraction didn't find one
                description = prop_schema_dict.get('description') or extracted_details.get('description')

                logger.debug(f"[{location_prefix}] Processing property '{name}', Required: {is_required}, Type: {param_schema.type}")
                param_info = ParameterInfo(
                    name=name, description=description,
                    required=is_required, location='body_property', # Indicate it's part of the body
                    schema_details=param_schema
                )
                parameters.append(param_info)
                processed_prop_names.add(name)
            except Exception as e:
                logger.warning(f"[{location_prefix}] Could not validate extracted schema details for property '{name}': {e}. Raw schema: {prop_schema_dict}. Skipping.", exc_info=True)
        return parameters, processed_prop_names


    def _parse_v3_parameters(self, operation: Dict, path_item: Dict) -> List[ParameterInfo]:
        """Parses parameters according to OpenAPI v3 structure, handling allOf."""
        parameters: List[ParameterInfo] = []
        processed_param_names = set() # Track all processed param names (body props, path, query etc)

        # 1. Request Body
        request_body = operation.get('requestBody')
        if request_body:
            logger.debug(f"[V3 Parser] Processing requestBody...")
            content = request_body.get('content', {}).get('application/json', {})
            schema = content.get('schema', {})
            resolved_schema = schema

            if '$ref' in schema:
                resolved_schema = self._resolve_ref(schema['$ref'])

            final_schema_type = resolved_schema.get('type')
            final_schema_keys = list(resolved_schema.keys()) if isinstance(resolved_schema, dict) else []
            logger.debug(f"[V3 Parser] Final schema for request body processing: type='{final_schema_type}', keys={final_schema_keys}")

            body_params: List[ParameterInfo] = []
            body_prop_names: set = set()

            # Handle allOf by merging properties and required fields
            if 'allOf' in resolved_schema and isinstance(resolved_schema['allOf'], list):
                logger.debug("[V3 Parser] Handling 'allOf' in request body schema.")
                combined_schema = {"properties": {}, "required": [], "type": "object"} # Assume object type for allOf result
                temp_required = set()

                for sub_schema_ref in resolved_schema['allOf']:
                    sub_schema = sub_schema_ref
                    if '$ref' in sub_schema:
                        sub_schema = self._resolve_ref(sub_schema['$ref'])

                    if sub_schema.get('type') == 'object' or 'properties' in sub_schema: # Check for properties even if type missing
                        combined_schema["properties"].update(sub_schema.get('properties', {}))
                    temp_required.update(sub_schema.get('required', []))

                combined_schema["required"] = sorted(list(temp_required)) # Store as sorted list
                body_params, body_prop_names = self._process_schema_properties(combined_schema, "V3 allOf")

            # Handle direct object with properties
            elif resolved_schema.get('type') == 'object' and 'properties' in resolved_schema:
                 body_params, body_prop_names = self._process_schema_properties(resolved_schema, "V3 direct")

            # Handle request body that is an array or primitive (not object/allOf)
            elif resolved_schema.get('type') in ['array', 'string', 'number', 'integer', 'boolean']:
                 logger.debug(f"[V3 Parser] Request body is a direct '{resolved_schema.get('type')}'")
                 try:
                      extracted_details = self._extract_schema_details(resolved_schema)
                      param_schema = ParameterSchema.model_validate(extracted_details)
                      # Use a conventional name or description if available
                      body_name = request_body.get('name', 'requestBody') # V2 might have name
                      description = request_body.get('description') or extracted_details.get('description')
                      is_required = request_body.get('required', False)
                      param_info = ParameterInfo(
                            name=body_name, description=description,
                            required=is_required, location='body', # Indicate it's the whole body
                            schema_details=param_schema
                      )
                      parameters.append(param_info)
                      processed_param_names.add(body_name)
                 except Exception as e:
                      logger.warning(f"[V3 Parser] Could not parse schema for non-object request body: {e}. Skipping.", exc_info=True)

            elif resolved_schema: # Check if schema exists but wasn't processed
                 logger.warning(f"[V3 Parser] Request body schema type '{final_schema_type}' with keys {final_schema_keys} was not processed.")
            else:
                 logger.debug("[V3 Parser] No processable schema found for request body.")

            parameters.extend(body_params)
            processed_param_names.update(body_prop_names)


        # 2. Path, Query, Header, Cookie Parameters
        path_level_params = {p['name']: p for p in path_item.get('parameters', []) if 'name' in p}
        op_level_params = {p['name']: p for p in operation.get('parameters', []) if 'name' in p}
        combined_params = {**path_level_params, **op_level_params}
        for name, param_def in combined_params.items():
            location = param_def.get('in'); schema_dict = param_def.get('schema', {})
            if not location or name in processed_param_names: continue # Avoid duplicates
            try:
                extracted_details = self._extract_schema_details(schema_dict)
                param_schema = ParameterSchema.model_validate(extracted_details)
                param_info = ParameterInfo(name=name, description=param_def.get('description'), required=param_def.get('required', False) or location == 'path', location=location, schema_details=param_schema)
                parameters.append(param_info); logger.debug(f"[V3 Parser] Parsed non-body parameter '{name}' in '{location}'")
                processed_param_names.add(name)
            except Exception as e: logger.warning(f"[V3 Parser] Could not validate extracted schema details for parameter '{name}' in '{location}': {e}. Raw schema: {schema_dict}. Skipping.", exc_info=True)

        return parameters

    # --- _parse_v2_parameters (Updated similarly) ---
    def _parse_v2_parameters(self, operation: Dict, path_item: Dict) -> List[ParameterInfo]:
        """Parses parameters according to OpenAPI v2 structure."""
        parameters: List[ParameterInfo] = []
        path_level_params = {p['name']: p for p in path_item.get('parameters', []) if 'name' in p}
        op_level_params = {p['name']: p for p in operation.get('parameters', []) if 'name' in p}
        combined_params = {**path_level_params, **op_level_params}
        processed_param_names = set()

        for name, param_def in combined_params.items():
            location = param_def.get('in'); required = param_def.get('required', False) or location == 'path'; description = param_def.get('description')
            if not location: logger.warning(f"[V2 Parser] Parameter '{name}' missing 'in'. Skipping."); continue

            param_schema_dict = {} # This will hold the schema details for validation

            if location == 'body':
                schema_ref = param_def.get('schema', {}); schema_dict = {}
                if '$ref' in schema_ref: schema_dict = self._resolve_ref(schema_ref['$ref'])
                else: schema_dict = schema_ref

                if schema_dict.get('type') == 'object' and 'properties' in schema_dict:
                    # Process object properties similar to V3
                    body_params, body_prop_names = self._process_schema_properties(schema_dict, "V2 Body")
                    parameters.extend(body_params)
                    processed_param_names.update(body_prop_names)
                    continue # Skip adding the main 'body' param itself
                else:
                    # Handle non-object body (array, primitive) - use the schema directly
                    param_schema_dict = schema_dict
                    location = 'body' # Keep original location for ParameterInfo

            elif location in ['query', 'header', 'path', 'formData']:
                 # Extract schema details directly from param definition keys
                 param_schema_dict = {k: param_def.get(k) for k in ['type', 'format', 'enum', 'default', 'items'] if param_def.get(k) is not None}
            else:
                 logger.warning(f"[V2 Parser] Unknown parameter location '{location}' for parameter '{name}'. Skipping.")
                 continue

            if name in processed_param_names: continue # Already processed as body property

            try:
                # Extract details *before* validation
                extracted_details = self._extract_schema_details(param_schema_dict if param_schema_dict else param_def)
                # Ensure type exists before validation
                if 'type' not in extracted_details:
                    logger.warning(f"[V2 Parser] Param '{name}' missing type, default 'string'.")
                    extracted_details['type'] = 'string'

                param_schema = ParameterSchema.model_validate(extracted_details)
                param_info = ParameterInfo(name=name, description=description, required=required, location=location, schema_details=param_schema)
                parameters.append(param_info); logger.debug(f"[V2 Parser] Parsed parameter '{name}' in '{location}'")
                processed_param_names.add(name)
            except Exception as e: logger.warning(f"[V2 Parser] Could not validate extracted schema for parameter '{name}' in '{location}': {e}. Raw: {param_schema_dict or param_def}. Skipping.", exc_info=True)
        return parameters


    # --- get_endpoint_info (Keep as before) ---
    def get_endpoint_info(self, target_path: str, target_method: str) -> Optional[EndpointInfo]:
        # (Logic remains the same - calls V2 or V3 parser based on version)
        target_method = target_method.lower()
        logger.debug(f"Getting endpoint info for: {target_method.upper()} {target_path} (Spec v{self.spec_version})")
        if not self.spec or 'paths' not in self.spec or target_path not in self.spec['paths']: logger.error(f"Path '{target_path}' not found."); return None
        path_item = self.spec['paths'][target_path]
        if target_method not in path_item: logger.error(f"Method '{target_method}' not found for path '{target_path}'."); return None
        operation = path_item[target_method]
        if self.spec_version == '3.0': all_parameters = self._parse_v3_parameters(operation, path_item)
        elif self.spec_version == '2.0': all_parameters = self._parse_v2_parameters(operation, path_item)
        else: logger.error("Unknown or unsupported specification version."); return None
        try:
            endpoint_info = EndpointInfo(path=target_path, method=target_method, summary=operation.get('summary'), operation_id=operation.get('operationId'), parameters=all_parameters)
            # Log required parameters found
            required_params = [p.name for p in all_parameters if p.required]
            logger.debug(f"Successfully parsed endpoint info for {target_method.upper()} {target_path}. Found {len(all_parameters)} params. Required: {required_params}")
            return endpoint_info
        except Exception as e: logger.error(f"Failed to create EndpointInfo model for {target_method.upper()} {target_path}: {e}", exc_info=True); return None


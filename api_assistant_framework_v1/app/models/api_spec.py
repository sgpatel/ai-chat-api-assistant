# app/models/api_spec.py
# Defines Pydantic models for structuring parsed OpenAPI data.

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class ParameterSchema(BaseModel):
    """Represents the schema details of a single parameter."""
    type: str
    description: Optional[str] = None
    format: Optional[str] = None
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    # For arrays
    items: Optional[Dict[str, Any]] = None # Could be another ParameterSchema for complex arrays
    # For objects
    properties: Optional[Dict[str, Any]] = None # Could be Dict[str, ParameterSchema]
    additionalProperties: Optional[bool | Dict[str, Any]] = None

class ParameterInfo(BaseModel):
    """Represents extracted information about a single API parameter."""
    name: str
    description: Optional[str] = None
    required: bool = False
    location: str # e.g., 'path', 'query', 'header', 'body_property'
    schema_details: ParameterSchema

class EndpointInfo(BaseModel):
    """Represents extracted information about a single API endpoint."""
    path: str
    method: str
    summary: Optional[str] = None
    operation_id: Optional[str] = None
    parameters: List[ParameterInfo] = Field(default_factory=list) # Combined list of all parameters


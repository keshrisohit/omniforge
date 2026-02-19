"""Schema validation for prompt variable schemas.

This module provides validation for prompt variable schemas using JSON Schema
and validates variable values against those schemas.
"""

from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from omniforge.prompts.models import VariableSchema


class SchemaValidator:
    """Validator for prompt variable schemas.

    This validator checks that variable schemas are valid JSON Schema
    and validates variable values against those schemas.

    Example:
        >>> validator = SchemaValidator()
        >>> schema = VariableSchema(
        ...     properties={"name": {"type": "string"}},
        ...     required=["name"]
        ... )
        >>> errors = validator.validate_schema(schema)
        >>> len(errors)
        0
    """

    # JSON Schema meta-schema for validation
    # Using Draft 7 which is widely supported
    SUPPORTED_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}

    def __init__(self) -> None:
        """Initialize schema validator."""
        pass

    def validate_schema(self, schema: VariableSchema) -> list[str]:
        """Validate that a variable schema is well-formed JSON Schema.

        Args:
            schema: The variable schema to validate

        Returns:
            List of error messages (empty if schema is valid)

        Example:
            >>> validator = SchemaValidator()
            >>> schema = VariableSchema(properties={"age": {"type": "integer"}})
            >>> errors = validator.validate_schema(schema)
            >>> len(errors)
            0
        """
        errors: list[str] = []

        # Convert VariableSchema to JSON Schema format
        json_schema = self._to_json_schema(schema)

        # Validate schema structure using JSON Schema validator
        try:
            Draft7Validator.check_schema(json_schema)
        except SchemaError as e:
            errors.append(f"Invalid JSON Schema: {e.message}")
            return errors

        # Additional validation for properties
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                prop_errors = self._validate_property_schema(prop_name, prop_schema)
                errors.extend(prop_errors)

        # Validate that required variables exist in properties
        for required_var in schema.required:
            if required_var not in schema.properties:
                errors.append(f"Required variable '{required_var}' is not defined in properties")

        return errors

    def validate_variables(self, variables: dict[str, Any], schema: VariableSchema) -> list[str]:
        """Validate variables against a schema.

        Args:
            variables: Dictionary of variable names to values
            schema: The variable schema to validate against

        Returns:
            List of validation error messages (empty if valid)

        Example:
            >>> validator = SchemaValidator()
            >>> schema = VariableSchema(
            ...     properties={"age": {"type": "integer"}},
            ...     required=["age"]
            ... )
            >>> errors = validator.validate_variables({"age": 25}, schema)
            >>> len(errors)
            0
        """
        errors: list[str] = []

        # Convert VariableSchema to JSON Schema format
        json_schema = self._to_json_schema(schema)

        # First validate the schema itself
        schema_errors = self.validate_schema(schema)
        if schema_errors:
            errors.append("Cannot validate variables against invalid schema")
            errors.extend(schema_errors)
            return errors

        # Validate variables against schema using jsonschema
        validator = Draft7Validator(json_schema)

        try:
            # Collect all validation errors
            validation_errors = list(validator.iter_errors(variables))

            for error in validation_errors:
                # Format error message with path information
                if error.path:
                    path_str = ".".join(str(p) for p in error.path)
                    error_msg = f"Variable '{path_str}': {error.message}"
                else:
                    error_msg = error.message

                errors.append(error_msg)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def _to_json_schema(self, schema: VariableSchema) -> dict[str, Any]:
        """Convert VariableSchema to standard JSON Schema format.

        Args:
            schema: The variable schema to convert

        Returns:
            Dictionary in JSON Schema format
        """
        json_schema: dict[str, Any] = {
            "type": "object",
            "properties": schema.properties,
            "required": schema.required,
        }

        return json_schema

    def _validate_property_schema(self, prop_name: str, prop_schema: dict[str, Any]) -> list[str]:
        """Validate a single property schema definition.

        Args:
            prop_name: Name of the property
            prop_schema: Schema definition for the property

        Returns:
            List of validation errors for this property
        """
        errors: list[str] = []

        # Check if type is specified
        if "type" not in prop_schema:
            errors.append(f"Property '{prop_name}' missing required 'type' field")
            return errors

        # Validate type value
        prop_type = prop_schema["type"]

        # Handle array of types (e.g., ["string", "null"])
        if isinstance(prop_type, list):
            invalid_types = [t for t in prop_type if t not in self.SUPPORTED_TYPES]
            if invalid_types:
                errors.append(
                    f"Property '{prop_name}' has invalid types: {', '.join(invalid_types)}"
                )
        elif prop_type not in self.SUPPORTED_TYPES:
            errors.append(f"Property '{prop_name}' has invalid type: {prop_type}")

        # Validate array-specific schema
        if prop_type == "array" or (isinstance(prop_type, list) and "array" in prop_type):
            if "items" in prop_schema:
                items_schema = prop_schema["items"]
                if isinstance(items_schema, dict):
                    # Validate items schema recursively
                    if "type" in items_schema:
                        item_type = items_schema["type"]
                        if isinstance(item_type, list):
                            invalid_types = [t for t in item_type if t not in self.SUPPORTED_TYPES]
                            if invalid_types:
                                errors.append(
                                    f"Property '{prop_name}' items have invalid types: "
                                    f"{', '.join(invalid_types)}"
                                )
                        elif item_type not in self.SUPPORTED_TYPES:
                            errors.append(
                                f"Property '{prop_name}' items have invalid type: {item_type}"
                            )

        # Validate object-specific schema
        if prop_type == "object" or (isinstance(prop_type, list) and "object" in prop_type):
            if "properties" in prop_schema:
                nested_props = prop_schema["properties"]
                if isinstance(nested_props, dict):
                    # Validate nested properties recursively
                    for nested_name, nested_schema in nested_props.items():
                        nested_errors = self._validate_property_schema(
                            f"{prop_name}.{nested_name}", nested_schema
                        )
                        errors.extend(nested_errors)

        return errors

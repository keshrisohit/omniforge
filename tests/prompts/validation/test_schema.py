"""Tests for schema validation."""

import pytest

from omniforge.prompts.models import VariableSchema
from omniforge.prompts.validation.schema import SchemaValidator


class TestSchemaValidator:
    """Tests for SchemaValidator class."""

    def test_validator_initialization(self) -> None:
        """SchemaValidator should initialize without errors."""
        validator = SchemaValidator()
        assert validator is not None

    def test_validate_empty_schema(self) -> None:
        """Validator should accept empty schema."""
        validator = SchemaValidator()
        schema = VariableSchema()
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_simple_string_property(self) -> None:
        """Validator should accept simple string property."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"name": {"type": "string"}})
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_multiple_property_types(self) -> None:
        """Validator should accept multiple valid property types."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
                "score": {"type": "number"},
                "tags": {"type": "array"},
                "metadata": {"type": "object"},
            }
        )
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_property_without_type(self) -> None:
        """Validator should reject property without type field."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"name": {"description": "A name"}})
        errors = validator.validate_schema(schema)

        assert len(errors) == 1
        assert "missing required 'type' field" in errors[0]

    def test_validate_property_with_invalid_type(self) -> None:
        """Validator should reject property with invalid type."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"data": {"type": "invalid_type"}})
        errors = validator.validate_schema(schema)

        assert len(errors) >= 1
        # Should have an error about the schema
        assert any("invalid" in error.lower() for error in errors)

    def test_validate_required_variable_exists(self) -> None:
        """Validator should accept required variable that exists in properties."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"name": {"type": "string"}}, required=["name"]
        )
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_required_variable_missing(self) -> None:
        """Validator should reject required variable not in properties."""
        validator = SchemaValidator()
        # Note: VariableSchema already validates this, so we bypass it
        # by creating the schema without validation
        schema = VariableSchema(properties={"name": {"type": "string"}})
        schema.required = ["age"]  # Set after creation to bypass pydantic validation
        errors = validator.validate_schema(schema)

        assert len(errors) == 1
        assert "not defined in properties" in errors[0]

    def test_validate_array_with_items_schema(self) -> None:
        """Validator should accept array with valid items schema."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"tags": {"type": "array", "items": {"type": "string"}}}
        )
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_array_with_invalid_items_type(self) -> None:
        """Validator should reject array with invalid items type."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"tags": {"type": "array", "items": {"type": "bad_type"}}}
        )
        errors = validator.validate_schema(schema)

        assert len(errors) >= 1
        assert any("invalid" in error.lower() for error in errors)

    def test_validate_object_with_nested_properties(self) -> None:
        """Validator should accept object with nested properties."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                }
            }
        )
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_object_with_invalid_nested_type(self) -> None:
        """Validator should reject object with invalid nested property type."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "user": {
                    "type": "object",
                    "properties": {"data": {"type": "invalid"}},
                }
            }
        )
        errors = validator.validate_schema(schema)

        assert len(errors) >= 1
        assert any("invalid" in error.lower() for error in errors)

    def test_validate_union_types(self) -> None:
        """Validator should accept union types (array of types)."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"value": {"type": ["string", "null"]}})
        errors = validator.validate_schema(schema)

        assert errors == []

    def test_validate_union_types_with_invalid_type(self) -> None:
        """Validator should reject union types with invalid type."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"value": {"type": ["string", "bad_type"]}})
        errors = validator.validate_schema(schema)

        assert len(errors) >= 1
        assert any("invalid" in error.lower() for error in errors)

    def test_validate_variables_with_valid_data(self) -> None:
        """Validator should accept variables matching schema."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"name": {"type": "string"}, "age": {"type": "integer"}},
            required=["name"],
        )
        variables = {"name": "Alice", "age": 30}
        errors = validator.validate_variables(variables, schema)

        assert errors == []

    def test_validate_variables_missing_required(self) -> None:
        """Validator should reject variables missing required fields."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"name": {"type": "string"}}, required=["name"]
        )
        variables = {"age": 30}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1
        assert any("name" in error.lower() for error in errors)

    def test_validate_variables_wrong_type(self) -> None:
        """Validator should reject variables with wrong type."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"age": {"type": "integer"}})
        variables = {"age": "not a number"}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1
        assert any("age" in error.lower() for error in errors)

    def test_validate_variables_extra_properties_allowed(self) -> None:
        """Validator should allow extra properties by default."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"name": {"type": "string"}})
        variables = {"name": "Alice", "extra": "data"}
        errors = validator.validate_variables(variables, schema)

        # Should be valid - extra properties allowed by default
        assert errors == []

    def test_validate_variables_nested_object(self) -> None:
        """Validator should validate nested object properties."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "user": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            },
            required=["user"],
        )
        variables = {"user": {"name": "Alice"}}
        errors = validator.validate_variables(variables, schema)

        assert errors == []

    def test_validate_variables_nested_object_missing_required(self) -> None:
        """Validator should detect missing required nested properties."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "user": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                }
            }
        )
        variables = {"user": {}}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1

    def test_validate_variables_array_items(self) -> None:
        """Validator should validate array items against schema."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"tags": {"type": "array", "items": {"type": "string"}}}
        )
        variables = {"tags": ["tag1", "tag2", "tag3"]}
        errors = validator.validate_variables(variables, schema)

        assert errors == []

    def test_validate_variables_array_items_wrong_type(self) -> None:
        """Validator should reject array with wrong item types."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"tags": {"type": "array", "items": {"type": "string"}}}
        )
        variables = {"tags": ["tag1", 123, "tag3"]}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1

    def test_validate_variables_with_invalid_schema(self) -> None:
        """Validator should return schema errors when schema is invalid."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"name": {"type": "invalid_type"}})
        variables = {"name": "Alice"}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1
        assert any("invalid schema" in error.lower() for error in errors)

    def test_validate_variables_empty_schema(self) -> None:
        """Validator should accept any variables with empty schema."""
        validator = SchemaValidator()
        schema = VariableSchema()
        variables = {"any": "data", "is": "valid"}
        errors = validator.validate_variables(variables, schema)

        assert errors == []

    def test_validate_variables_empty_variables(self) -> None:
        """Validator should accept empty variables when nothing required."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"name": {"type": "string"}})
        variables = {}
        errors = validator.validate_variables(variables, schema)

        # Should be valid - no required fields
        assert errors == []

    def test_validate_variables_empty_variables_with_required(self) -> None:
        """Validator should reject empty variables when fields required."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={"name": {"type": "string"}}, required=["name"]
        )
        variables = {}
        errors = validator.validate_variables(variables, schema)

        assert len(errors) >= 1
        assert any("name" in error.lower() for error in errors)

    def test_validate_variables_boolean_type(self) -> None:
        """Validator should validate boolean types correctly."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"active": {"type": "boolean"}})

        # Valid boolean
        errors = validator.validate_variables({"active": True}, schema)
        assert errors == []

        # Invalid boolean
        errors = validator.validate_variables({"active": "yes"}, schema)
        assert len(errors) >= 1

    def test_validate_variables_number_vs_integer(self) -> None:
        """Validator should distinguish between number and integer types."""
        validator = SchemaValidator()

        # Integer schema accepts integers
        int_schema = VariableSchema(properties={"value": {"type": "integer"}})
        errors = validator.validate_variables({"value": 42}, int_schema)
        assert errors == []

        # Number schema accepts both integers and floats
        num_schema = VariableSchema(properties={"value": {"type": "number"}})
        errors = validator.validate_variables({"value": 42.5}, num_schema)
        assert errors == []

    def test_validate_variables_null_type(self) -> None:
        """Validator should validate null type correctly."""
        validator = SchemaValidator()
        schema = VariableSchema(properties={"value": {"type": ["string", "null"]}})

        # Valid null
        errors = validator.validate_variables({"value": None}, schema)
        assert errors == []

        # Valid string
        errors = validator.validate_variables({"value": "text"}, schema)
        assert errors == []

    def test_validate_complex_schema(self) -> None:
        """Validator should handle complex nested schemas."""
        validator = SchemaValidator()
        schema = VariableSchema(
            properties={
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "emails": {"type": "array", "items": {"type": "string"}},
                        "settings": {
                            "type": "object",
                            "properties": {"theme": {"type": "string"}},
                        },
                    },
                    "required": ["name"],
                }
            },
            required=["user"],
        )

        variables = {
            "user": {
                "name": "Alice",
                "age": 30,
                "emails": ["alice@example.com"],
                "settings": {"theme": "dark"},
            }
        }

        errors = validator.validate_variables(variables, schema)
        assert errors == []

import pytest
import json
import jsonschema
from pathlib import Path
from src.dimension_extractor.json_handler import JSONParser, JSONPrettyPrinter
from hypothesis import given, settings, HealthCheck, strategies as st

@pytest.fixture
def dummy_schema(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
        },
        "required": ["name", "value"],
        "additionalProperties": False
    }
    with open(schema_path, 'w') as f:
        json.dump(schema, f)
    return schema_path

@pytest.fixture
def valid_json(tmp_path):
    json_path = tmp_path / "data.json"
    with open(json_path, 'w') as f:
        json.dump({"name": "test", "value": 123}, f)
    return json_path

@pytest.fixture
def invalid_json(tmp_path):
    json_path = tmp_path / "invalid.json"
    with open(json_path, 'w') as f:
        json.dump({"name": "test"}, f)
    return json_path

def test_json_parser_valid(dummy_schema, valid_json):
    parser = JSONParser(dummy_schema)
    data = parser.parse(valid_json)
    assert data["name"] == "test"
    assert data["value"] == 123

def test_json_parser_invalid(dummy_schema, invalid_json):
    parser = JSONParser(dummy_schema)
    with pytest.raises(ValueError, match="JSON validation error"):
        parser.parse(invalid_json)

def test_json_pretty_printer(dummy_schema, tmp_path):
    printer = JSONPrettyPrinter(dummy_schema)
    out_path = tmp_path / "out.json"
    printer.print({"name": "print_test", "value": 456}, out_path)
    
    with open(out_path, 'r') as f:
        data = json.load(f)
        assert data["name"] == "print_test"
        assert data["value"] == 456

def test_json_pretty_printer_invalid(dummy_schema, tmp_path):
    printer = JSONPrettyPrinter(dummy_schema)
    out_path = tmp_path / "out.json"
    with pytest.raises(ValueError, match="Output data does not match schema"):
        printer.print({"name": "print_test"}, out_path)

# Feature: dimension-extraction-system, Property 1: JSON Round-Trip Preservation
# Feature: dimension-extraction-system, Property 13: JSON Schema Compliance
# Feature: dimension-extraction-system, Property 14: Output Completeness
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.text(), value=st.integers() | st.floats(allow_nan=False, allow_infinity=False))
def test_property_json_roundtrip_and_compliance(dummy_schema, tmp_path, name, value):
    printer = JSONPrettyPrinter(dummy_schema)
    parser = JSONParser(dummy_schema)
    
    out_path = tmp_path / "roundtrip.json"
    data = {"name": name, "value": value}
    
    # Property 13: Output Compliance & Property 14: Output Completeness
    printer.print(data, out_path)
    
    # Property 1: Round-trip
    parsed_data = parser.parse(out_path)
    
    assert parsed_data["name"] == name
    assert parsed_data["value"] == value

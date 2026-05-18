import json
from pathlib import Path
from typing import Dict, Any, Optional
import jsonschema

class JSONParser:
    def __init__(self, schema_path: Optional[Path] = None):
        self.schema = self._load_schema(schema_path) if schema_path else None

    def _load_schema(self, schema_path: Path) -> Dict[str, Any]:
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        with open(schema_path, 'r') as f:
            return json.load(f)

    def parse(self, json_path: Path) -> Dict[str, Any]:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if self.schema:
            try:
                jsonschema.validate(instance=data, schema=self.schema)
            except jsonschema.exceptions.ValidationError as e:
                raise ValueError(f"JSON validation error: {e.message}")
        
        return data

class JSONPrettyPrinter:
    def __init__(self, schema_path: Optional[Path] = None):
        self.schema = None
        if schema_path and schema_path.exists():
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)

    def print(self, output_data: Dict[str, Any], json_path: Path):
        if self.schema:
            try:
                jsonschema.validate(instance=output_data, schema=self.schema)
            except jsonschema.exceptions.ValidationError as e:
                raise ValueError(f"Output data does not match schema: {e.message}")
                
        with open(json_path, 'w') as f:
            json.dump(output_data, f, indent=2, sort_keys=True)

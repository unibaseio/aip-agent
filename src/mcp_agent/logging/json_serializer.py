from typing import Any, Dict, Iterable, Set
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from enum import Enum
import dataclasses
import inspect
import httpx


class JSONSerializer:
    """
    A robust JSON serializer that handles various Python objects by attempting
    different serialization strategies recursively.
    """

    def __init__(self):
        # Set of already processed objects to prevent infinite recursion
        self._processed_objects: Set[int] = set()

    def serialize(self, obj: Any) -> Any:
        """Main entry point for serialization."""
        # Reset processed objects for new serialization
        self._processed_objects.clear()
        return self._serialize_object(obj)

    def _serialize_object(self, obj: Any) -> Any:
        """Recursively serialize an object using various strategies."""
        # Handle None
        if obj is None:
            return None

        # Prevent infinite recursion
        obj_id = id(obj)
        if obj_id in self._processed_objects:
            return str(obj)
        self._processed_objects.add(obj_id)

        # Try different serialization strategies in order
        try:
            if isinstance(obj, httpx.Response):
                return f"<httpx.Response [{obj.status_code}] {obj.url}>"

            # Basic JSON-serializable types
            if isinstance(obj, (str, int, float, bool)):
                return obj

            # Handle common built-in types
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if isinstance(obj, (Decimal, UUID)):
                return str(obj)
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, Enum):
                return obj.value

            # Handle callables
            if callable(obj):
                return f"<callable: {obj.__name__}>"

            # Handle Pydantic models
            if hasattr(obj, "model_dump"):  # Pydantic v2
                return self._serialize_object(obj.model_dump())
            if hasattr(obj, "dict"):  # Pydantic v1
                return self._serialize_object(obj.dict())

            # Handle dataclasses
            if dataclasses.is_dataclass(obj):
                return self._serialize_object(dataclasses.asdict(obj))

            # Handle objects with custom serialization method
            if hasattr(obj, "to_json"):
                return self._serialize_object(obj.to_json())
            if hasattr(obj, "to_dict"):
                return self._serialize_object(obj.to_dict())

            # Handle dictionaries
            if isinstance(obj, Dict):
                return {
                    str(key): self._serialize_object(value)
                    for key, value in obj.items()
                }

            # Handle iterables (lists, tuples, sets)
            if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
                return [self._serialize_object(item) for item in obj]

            # Handle objects with __dict__
            if hasattr(obj, "__dict__"):
                return self._serialize_object(obj.__dict__)

            # Handle objects with attributes
            if inspect.getmembers(obj):
                return {
                    name: self._serialize_object(value)
                    for name, value in inspect.getmembers(obj)
                    if not name.startswith("_") and not inspect.ismethod(value)
                }

            # Fallback: convert to string
            return str(obj)

        except Exception as e:
            # If all serialization attempts fail, return string representation
            return f"<unserializable: {type(obj).__name__}, error: {str(e)}>"

    def __call__(self, obj: Any) -> Any:
        """Make the serializer callable."""
        return self.serialize(obj)

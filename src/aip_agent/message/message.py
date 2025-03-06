from typing import Any, Optional
from pydantic import BaseModel


from dataclasses import dataclass

@dataclass
class FunctionCall:
    id: str
    # JSON args
    arguments: str
    # Function to call
    name: str

class FunctionExecutionResult(BaseModel):
    """Function execution result contains the output of a function call."""

    content: str
    """The output of the function call."""

    name: str
    """The name of the function that was called."""

    call_id: str
    """The ID of the function call. Note this ID may be empty for some models."""

    is_error: bool | None = None
    """Whether the function call resulted in an error."""

class InteractionMessage(BaseModel):
    """A generic interaction message type for agent communications.
    
    This message type can be used for various types of interactions between agents,
    such as listing tools, getting agent capabilities, etc.
    
    Attributes:
        type (str): The type of interaction.
            This determines how the agent should handle the message.
        source (Optional[str]): The source of the interaction message.
            This can be used to identify where the message originated from.
            Defaults to None.
        content (Optional[Any]): Additional content or parameters for the interaction.
            Defaults to None.
        auth (Optional[Any]): Additional authentication information for the interaction.
            Defaults to None.
    
    Example usage:
    ```python
    # List tools interaction
    list_tools_msg = InteractionMessage(
        type="list_tools",
        source="user_interface"
    )
    
    # Get capabilities interaction
    capabilities_msg = InteractionMessage(
        type="get_capabilities",
        source="system"
    )
    
    # Custom interaction with content
    custom_msg = InteractionMessage(
        type="custom_action",
        content={"action": "parameters"},
        source="external_service"
    )
    ```
    """
    action: str
    source: Optional[str] = None
    content: Optional[Any] = None
    auth: Optional[Any] = None
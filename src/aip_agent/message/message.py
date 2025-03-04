from typing import Any, Optional
from pydantic import BaseModel

class InteractionMessage(BaseModel):
    """A generic interaction message type for agent communications.
    
    This message type can be used for various types of interactions between agents,
    such as listing tools, getting agent capabilities, etc.
    
    Attributes:
        type (str): The type of interaction.
            This determines how the agent should handle the message.
        content (Optional[Any]): Additional content or parameters for the interaction.
            Defaults to None.
        source (Optional[str]): The source of the interaction message.
            This can be used to identify where the message originated from.
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
    content: Optional[Any] = None
    source: Optional[str] = None
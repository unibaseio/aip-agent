import json
from dataclasses import dataclass
from typing import List, Optional, Literal, Dict, Any


from autogen_core import FunctionCall, MessageContext, RoutedAgent, message_handler
from autogen_core.models import FunctionExecutionResult
from autogen_core.tools import Tool

from aip_agent.message.message import InteractionMessage

__all__ = [
    "ToolAgent",
    "ToolException",
    "ToolNotFoundException",
    "InvalidToolArgumentsException",
    "ToolExecutionException",
]


@dataclass
class ToolException(BaseException):
    call_id: str
    content: str


@dataclass
class ToolNotFoundException(ToolException):
    pass


@dataclass
class InvalidToolArgumentsException(ToolException):
    pass


@dataclass
class ToolExecutionException(ToolException):
    pass


class ToolAgent(RoutedAgent):
    """A tool agent accepts direct messages of the type `FunctionCall`,
    executes the requested tool with the provided arguments, and returns the
    result as `FunctionExecutionResult` messages.

    Args:
        description (str): The description of the agent.
        tools (List[Tool]): The list of tools that the agent can execute.
    """

    def __init__(
        self,
        description: str,
        tools: List[Tool],
    ) -> None:
        super().__init__(description)
        self._tools = tools

    @property
    def tools(self) -> List[Tool]:
        return self._tools

    @message_handler
    async def handle_request(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        """Handle various types of requests to the agent.

        Args:
            message (InteractionMessage): The request message.
            ctx (MessageContext): The message context.

        Returns:
            InteractionMessage: The response to the request.

        Raises:
            ValueError: If the request type is not supported.
        """
        print("handle tool list")
        if message.action == "list_tools":
            tools_info = []
            for tool in self._tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                if tool.schema and "parameters" in tool.schema:
                    tool_info["inputSchema"] = tool.schema["parameters"]
                tools_info.append(tool_info)
            return InteractionMessage(
                action="response",
                content={
                    "tools": tools_info,
                    "total": len(tools_info)
                }
            )
        elif message.action == "get_capabilities":
            return InteractionMessage(
                action="response",
                content={
                    "description": self.description,
                    "supported_request_types": ["list_tools", "get_capabilities"],
                    "tool_count": len(self._tools),
                    "version": "1.0"
                }
            )
        else:
            raise ValueError(f"Unsupported request type: {message.action}")

    @message_handler
    async def handle_function_call(self, message: FunctionCall, ctx: MessageContext) -> FunctionExecutionResult:
        """Handles a `FunctionCall` message by executing the requested tool with the provided arguments.

        Args:
            message (FunctionCall): The function call message.
            cancellation_token (CancellationToken): The cancellation token.

        Returns:
            FunctionExecutionResult: The result of the function execution.

        Raises:
            ToolNotFoundException: If the tool is not found.
            InvalidToolArgumentsException: If the tool arguments are invalid.
            ToolExecutionException: If the tool execution fails.
        """
        tool = next((tool for tool in self._tools if tool.name == message.name), None)
        if tool is None:
            raise ToolNotFoundException(call_id=message.id, content=f"Error: Tool not found: {message.name}")
        else:
            try:
                arguments = json.loads(message.arguments)
                result = await tool.run_json(args=arguments, cancellation_token=ctx.cancellation_token)
                result_as_str = tool.return_value_as_string(result)
            except json.JSONDecodeError as e:
                print(f"handle tool1: {message.id} {e}")
                raise InvalidToolArgumentsException(
                    call_id=message.id, content=f"Error: Invalid arguments: {message.arguments}"
                ) from e
            except Exception as e:
                print(f"handle tool2: {message.id} {e}")
                raise ToolExecutionException(call_id=message.id, content=f"Error: {e}") from e
        return FunctionExecutionResult(content=result_as_str, call_id=message.id, is_error=False, name=message.name)

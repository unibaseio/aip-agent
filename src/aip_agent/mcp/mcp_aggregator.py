from asyncio import Lock, gather
import json
from typing import List, Dict, Optional, TYPE_CHECKING
import uuid
import asyncio

from pydantic import BaseModel, ConfigDict
from mcp.client.session import ClientSession
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    Tool,
    TextContent,
)

from aip_agent.logging.logger import get_logger
from aip_agent.mcp.gen_client import gen_client

from aip_agent.config import MCPServerSettings
from aip_agent.context_dependent import ContextDependent
from aip_agent.mcp.mcp_agent_client_session import MCPAgentClientSession
from aip_agent.mcp.mcp_connection_manager import MCPConnectionManager

from aip_agent.message.message import InteractionMessage, FunctionCall,FunctionExecutionResult

from autogen_core import AgentId
from autogen_core import AgentRuntime

if TYPE_CHECKING:
    from aip_agent.context import Context


logger = get_logger(__name__)

SEP = "-"


class NamespacedTool(BaseModel):
    """
    A tool that is namespaced by server name.
    """

    tool: Tool
    server_name: str
    namespaced_tool_name: str


class MCPAggregator(ContextDependent):
    """
    Aggregates multiple MCP servers. When a developer calls, e.g. call_tool(...),
    the aggregator searches all servers in its list for a server that provides that tool.
    """

    initialized: bool = False
    """Whether the aggregator has been initialized with tools and resources from all servers."""

    connection_persistence: bool = False
    """Whether to maintain a persistent connection to the server."""

    server_names: List[str]
    """A list of server names to connect to."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    async def __aenter__(self):
        if self.initialized:
            return self

        # Keep a connection manager to manage persistent connections for this aggregator
        if self.connection_persistence:
            self._persistent_connection_manager = MCPConnectionManager(
                self.context.server_registry
            )
            await self._persistent_connection_manager.__aenter__()

        logger.info("Loading servers in aenter...")
        await self.load_servers()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __init__(
        self,
        name: str,
        server_names: List[str],
        runtime: AgentRuntime,
        connection_persistence: bool = False,
        context: Optional["Context"] = None,
        **kwargs,
    ):
        """
        :param server_names: A list of server names to connect to.
        :param runtime: The agent runtime to use
        :param connection_persistence: Whether to maintain persistent connections
        :param context: Optional context for dependency injection
        Note: The server names must be resolvable by the gen_client function, and specified in the server registry.
        """
        super().__init__(
            context=context,
            **kwargs,
        )

        self.server_names = server_names
        self.connection_persistence = connection_persistence

        self._persistent_connection_manager: MCPConnectionManager = None

        # Maps namespaced_tool_name -> namespaced tool info
        self._namespaced_tool_map: Dict[str, NamespacedTool] = {}
        # Maps server_name -> list of tools
        self._server_to_tool_map: Dict[str, List[NamespacedTool]] = {}
        self._tool_map_lock = Lock()

        self._name = name
        self._grpc_runtime: AgentRuntime = runtime
        self._grpc_server_map: Dict[str, str] = {}

        # TODO: saqadri - add resources and prompt maps as well

    async def close(self):
        """
        Close all persistent connections when the aggregator is deleted.
        """
        if self.connection_persistence and self._persistent_connection_manager:
            try:
                await self._persistent_connection_manager.disconnect_all()
                self.initialized = False
            finally:
                await self._persistent_connection_manager.__aexit__(None, None, None)

    @classmethod
    async def create(
        cls,
        server_names: List[str],
        connection_persistence: bool = False,
    ) -> "MCPAggregator":
        """
        Factory method to create and initialize an MCPAggregator.
        Use this instead of constructor since we need async initialization.
        If connection_persistence is True, the aggregator will maintain a
        persistent connection to the servers for as long as this aggregator is around.
        By default we do not maintain a persistent connection.
        """

        logger.info(f"Creating MCPAggregator with servers: {server_names}")

        instance = cls(
            server_names=server_names,
            connection_persistence=connection_persistence,
        )

        try:
            await instance.__aenter__()

            logger.info("Loading servers...")
            await instance.load_servers()

            logger.debug("MCPAggregator created and initialized.")
            return instance
        except Exception as e:
            logger.error(f"Error creating MCPAggregator: {e}")
            await instance.__aexit__(None, None, None)

    async def load_servers(self):
        """
        Discover tools from each server in parallel and build an index of namespaced tool names.
        """
        if self.initialized:
            logger.warning("MCPAggregator already initialized.")
            return
        
        async with self._tool_map_lock:
            self._namespaced_tool_map.clear()
            self._server_to_tool_map.clear()

        server_names = []
        for server_name in self.server_names:
            if server_name in self._grpc_server_map:
                continue
            if server_name in self.context.config.mcp.servers:
                if self.context.config.mcp.servers[server_name].transport == "aip-grpc":
                    await self.load_grpc_server(server_name)
                else:
                    server_names.append(server_name)
            else:
                logger.warning(f"Server {server_name} not found in config")

        for server_name in server_names:
            if self.connection_persistence:
                logger.info(f"Loading server: {server_name}")
                await self._persistent_connection_manager.get_server(
                    server_name, client_session_factory=MCPAgentClientSession
                )

        async def fetch_tools(client: ClientSession):
            try:
                result: ListToolsResult = await client.list_tools()
                return result.tools or []
            except Exception as e:
                logger.error(f"Error loading tools from server '{server_name}'", data=e)
                return []

        async def load_server_tools(server_name: str):
            tools: List[Tool] = []
            if self.connection_persistence:
                server_connection = (
                    await self._persistent_connection_manager.get_server(
                        server_name, client_session_factory=MCPAgentClientSession
                    )
                )
                tools = await fetch_tools(server_connection.session)
                
            else:
                async with gen_client(
                    server_name, server_registry=self.context.server_registry
                ) as client:
                    tools = await fetch_tools(client)

            return server_name, tools

        # Gather tools from all servers concurrently
        results = await gather(
            *(load_server_tools(server_name) for server_name in self.server_names),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, BaseException):
                continue
            server_name, tools = result

            self._server_to_tool_map[server_name] = []
            for tool in tools:
                logger.info(f"{server_name} has tool: {tool}")
                namespaced_tool_name = f"{server_name}{SEP}{tool.name}"
                namespaced_tool = NamespacedTool(
                    tool=tool,
                    server_name=server_name,
                    namespaced_tool_name=namespaced_tool_name,
                )

                self._namespaced_tool_map[namespaced_tool_name] = namespaced_tool
                self._server_to_tool_map[server_name].append(namespaced_tool)

        self.initialized = True

    async def load_grpc_server(self, server_name):
        response = await self._grpc_runtime.send_message(InteractionMessage(
            action="list_tools",
            content=""
        ), AgentId(server_name, "default"), sender=AgentId(self._name, "default"))
        
        try:
            if not isinstance(response.content, dict):
                logger.error(f"Invalid response format from server {server_name}: content is not a dict type")
                return server_name
                
            tools_data = response.content.get("tools", [])
            if not isinstance(tools_data, list):
                logger.error(f"Invalid tools format from server {server_name}: tools is not a list")
                return server_name
                
            if not tools_data:
                logger.warning(f"No tools returned from server {server_name}")
                return server_name
                
        except Exception as e:
            logger.error(f"Error processing tools from server {server_name}: {str(e)}")
            return server_name
            
        self._server_to_tool_map[server_name] = []
        for tool_data in tools_data:
            try:
                if not isinstance(tool_data, dict):
                    logger.error(f"Invalid tool format from server {server_name}: tool is not a dictionary")
                    continue
    
                tool = Tool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description"),
                    inputSchema=tool_data.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                )
                
                logger.info(f"{server_name} has tool: {tool}")
                namespaced_tool_name = f"{server_name}{SEP}{tool.name}"
                namespaced_tool = NamespacedTool(
                    tool=tool,
                    server_name=server_name,
                    namespaced_tool_name=namespaced_tool_name,
                )
                self._namespaced_tool_map[namespaced_tool_name] = namespaced_tool
                self._server_to_tool_map[server_name].append(namespaced_tool)
            except Exception as e:
                logger.error(f"Error processing tool from server {server_name}: {str(e)}")
                continue

        self.server_names.append(server_name)
        self._grpc_server_map[server_name] = server_name
        return server_name

    async def load_server(self, server_name: str, url: str):
        """
        connect server with url over aip-sse or aip-grpc
        """
        if server_name in self._server_to_tool_map:
            print(f"already has server: {server_name}")
            return server_name
        
        # use runtime(grpc implementation) to connect to server
        if "grpc" in url:
            self.context.config.mcp.servers[server_name] = MCPServerSettings(
                name=server_name,
                transport='aip-grpc'
            )
            await self.load_grpc_server(server_name)
            return server_name

        # use aip-sse to connect to server
        self.context.config.mcp.servers[server_name] = MCPServerSettings(
            name=server_name,
            transport='aip-sse',
            url=url
        )

        logger.info(f"Adding server: {server_name}")
        await self._persistent_connection_manager.get_server(
                server_name, client_session_factory=MCPAgentClientSession
        )

        async def fetch_tools(client: ClientSession):
            try:
                result: ListToolsResult = await client.list_tools()
                return result.tools or []
            except Exception as e:
                logger.error(f"Error loading tools from server '{server_name}'", data=e)
                return []

        async def load_server_tool():
            tools: List[Tool] = []
            server_connection = (
            await self._persistent_connection_manager.get_server(
                        server_name, client_session_factory=MCPAgentClientSession
                    )
                )
            tools = await fetch_tools(server_connection.session)

            return tools
        
         # Gather tools from all servers concurrently
        tools = await load_server_tool()

        self._server_to_tool_map[server_name] = []
        for tool in tools:
            logger.info(f"{server_name} has tool: {tool}")
            namespaced_tool_name = f"{server_name}{SEP}{tool.name}"
            namespaced_tool = NamespacedTool(
                tool=tool,
                server_name=server_name,
                namespaced_tool_name=namespaced_tool_name,
            )
            self._namespaced_tool_map[namespaced_tool_name] = namespaced_tool
            self._server_to_tool_map[server_name].append(namespaced_tool)

        self.server_names.append(server_name)
        return server_name

    async def list_servers(self) -> List[str]:
        """Return the list of server names aggregated by this agent."""
        if not self.initialized:
            await self.load_servers()

        return self.server_names

    async def list_tools(self) -> ListToolsResult:
        """
        :return: Tools from all servers aggregated, and renamed to be dot-namespaced by server name.
        """
        if not self.initialized:
            await self.load_servers()

        return ListToolsResult(
            tools=[
                namespaced_tool.tool.model_copy(update={"name": namespaced_tool_name})
                for namespaced_tool_name, namespaced_tool in self._namespaced_tool_map.items()
            ]
        )

    async def list_tool(self, server_name: str) -> ListToolsResult:
        """
        :return: Tools of server_name, and renamed to be dot-namespaced by server name.
        """
        if not self.initialized:
            await self.load_servers()

        return ListToolsResult(
            tools=[
                namespaced_tool.tool.model_copy(update={"name": namespaced_tool.namespaced_tool_name})
                for namespaced_tool in self._server_to_tool_map[server_name]
            ]
        )

    async def send_message(self, agent_name: str, content: str):
        """
        Send a message to a specified agent and wait for its response. @agent_name is the name of the agent to send the message to.
        For example:
        1. Direct agent communication: "@agent_weather What's the weather like?", 
           agent_name should be "agent_weather" and content should be "What's the weather like?"
        2. Task delegation: "ask agent_data Please analyze this data", 
           agent_name should be "agent_data" and content should be "Please analyze this data"
        3. Multi-agent collaboration: "ask @agent_helper Can you help me?", 
           agent_name should be "agent_helper" and content should be "Can you help me?"

        Args:
            agent_name (str): The name of the target agent to send the message to.
            content (str): The message content to be sent.

        Returns:
            The response message from the target agent.

        Raises:
            TimeoutError: If the agent does not respond within 120 seconds.
            Exception: If there are any other errors during message sending.
        """
        try:
            res = await asyncio.wait_for(
                self._grpc_runtime.send_message(
                    InteractionMessage(
                        action="ask",
                        content=content,
                        source=self._name
                    ),
                    AgentId(agent_name, "default"),
                    sender=AgentId(self._name, "default")
                ),
                timeout=120.0  # 120 seconds timeout
            )
            return res
        except asyncio.TimeoutError:
            print(f"Error: Message to {agent_name} timed out after 60 seconds")
            return f"Error: Message sending timed out, {agent_name} is offline"
        except Exception as e:
            print(f"Error: sending message to {agent_name}: {e}")
            return f"Error: sending message to {agent_name}: {e}"

    async def call_grpc_tool(
        self, server_name: str, tool_name: str, arguments: dict | None = None
    ) -> CallToolResult:
        """
        Call a tool using grpc implementation
        """
        response = await self._grpc_runtime.send_message(
            FunctionCall(
                id=str(uuid.uuid4()),
                name=tool_name,
                arguments=json.dumps(arguments)
            ),
            AgentId(server_name, "default"),
            sender=AgentId(self._name, "default")
        )
        
        try:
            if not isinstance(response, FunctionExecutionResult):
                logger.error(f"Invalid response format from {server_name}, {arguments}, {response}")
                return CallToolResult(isError=True, content=[TextContent(type="text", text="Invalid response format")])
                
            if response.is_error:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=response.content or "Tool execution failed")]
                )
                
            content = [TextContent(type="text", text=response.content)]
            return CallToolResult(
                isError=False,
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error processing tool execution result from server {server_name}: {str(e)}")
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error processing tool execution result: {str(e)}")]
            )

    async def call_tool(
        self, name: str, arguments: dict | None = None
    ) -> CallToolResult:
        """
        Call a namespaced tool, e.g., 'server_name.tool_name'.
        """

        if not self.initialized:
            await self.load_servers()

        server_name: str = None
        local_tool_name: str = None

        if SEP in name:  # Namespaced tool name
            server_name, local_tool_name = name.split(SEP, 1)
        else:
            # Assume un-namespaced, loop through all servers to find the tool. First match wins.
            for _, tools in self._server_to_tool_map.items():
                for namespaced_tool in tools:
                    if namespaced_tool.tool.name == name:
                        server_name = namespaced_tool.server_name
                        local_tool_name = name
                        break

            if server_name is None or local_tool_name is None:
                error_message = f"Tool '{name}' not found"
                logger.error(error_message)
                return CallToolResult(
                    isError=True,
                    content=[TextContent(text=error_message)]
                )

        logger.info(
            f"MCPServerAggregator: Requesting tool call '{name}'. Calling tool '{local_tool_name}' on server '{server_name}'"
        )

        if server_name in self._grpc_server_map:
            return await self.call_grpc_tool(server_name, local_tool_name, arguments)

        async def try_call_tool(client: ClientSession):
            try:
                return await client.call_tool(name=local_tool_name, arguments=arguments)
            except Exception as e:
                error_message = f"Failed to call tool '{local_tool_name}' on server '{server_name}': {e}"
                return CallToolResult(
                    isError=True,
                    content=[TextContent(text=error_message)]
                )

        if self.connection_persistence:
            server_connection = await self._persistent_connection_manager.get_server(
                server_name, client_session_factory=MCPAgentClientSession
            )

            return await try_call_tool(server_connection.session)
        else:
            async with gen_client(
                server_name, server_registry=self.context.server_registry
            ) as client:
                return await try_call_tool(client)


class MCPCompoundServer(Server):
    """
    A compound server (server-of-servers) that aggregates multiple MCP servers and is itself an MCP server
    """

    def __init__(self, server_names: List[str], name: str = "MCPCompoundServer"):
        super().__init__(name)
        self.aggregator = MCPAggregator(server_names)

        # Register handlers
        # TODO: saqadri - once we support resources and prompts, add handlers for those as well
        self.list_tools()(self._list_tools)
        self.call_tool()(self._call_tool)

    async def _list_tools(self) -> List[Tool]:
        """List all tools aggregated from connected MCP servers."""
        tools_result = await self.aggregator.list_tools()
        return tools_result.tools

    async def _call_tool(
        self, name: str, arguments: dict | None = None
    ) -> CallToolResult:
        """Call a specific tool from the aggregated servers."""
        try:
            result = await self.aggregator.call_tool(name=name, arguments=arguments)
            return result.content
        except Exception as e:
            return CallToolResult(isError=True, message=f"Error calling tool: {e}")

    async def run_stdio_async(self) -> None:
        """Run the server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=self.create_initialization_options(),
            )

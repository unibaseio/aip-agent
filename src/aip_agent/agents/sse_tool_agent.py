import datetime
import json
import logging
import os
import time
from typing import Optional, Any
import uuid
from autogen_core import (
    AgentId,
    try_get_known_serializers_for_type,
)


from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
from mcp.server.fastmcp import FastMCP

from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.message.message import InteractionMessage, FunctionCall, FunctionExecutionResult

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import Scope, Receive, Send
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager

from membase.chain.chain import membase_chain, membase_account, membase_id
from membase.auth import verify_sign

def verify_header(auth_header: dict[Any, Any]):
    agent_id = auth_header.get(b'x-agent')
    signature = auth_header.get(b'x-sign')
    timestamp = auth_header.get(b'x-timestamp')

    logging.debug(f"auth time: {timestamp}, agent: {agent_id}, sign: {signature}")
   
    if not signature or not timestamp or not agent_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    agent_id = agent_id.decode('utf-8')
    signature = signature.decode('utf-8')

    try:
        verify_sign(agent_id, timestamp, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not membase_chain.has_auth(membase_id, agent_id):
        logging.warning(f"{agent_id} is not auth on chain")
        raise HTTPException(status_code=400, detail="No auth on chain")

class BasicAuthTransport(SseServerTransport):
    def __init__(self, endpoint: str):
        super().__init__(endpoint)

    @asynccontextmanager
    async def connect_sse(self, scope: Scope, receive: Receive, send: Send):
        try:
            auth_header = dict(scope["headers"])
            verify_header(auth_header)
        except Exception as e:
            raise e
        logging.info("sse message auth sign pass")
        async with super().connect_sse(scope, receive, send) as streams:
            yield streams

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""

    logging.info(f"start with account: {membase_account} and id: {membase_id}")

    sse = BasicAuthTransport("/messages/")
    
    async def handle_sse(request: Request) -> None:
        try:
            auth_header = dict(request.scope["headers"])
            verify_header(auth_header)
        except Exception as e:
            raise e
        logging.info("sse auth sign pass")
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                server_name=membase_id,
                server_version="0.1.4",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                    ),
                )
            )

    from starlette.responses import JSONResponse
    async def info(request):
        info_data = {
            "uuid": membase_id,
        }
        return JSONResponse(info_data)

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
            Route("/info", endpoint=info)
        ],
    )

class SSEToolAgentWrapper:
    """A wrapper class that manages ToolAgent with common infrastructure"""
    
    def __init__(
        self,
        name: str,
        server: FastMCP,
        host_address: str = '13.212.116.103:8081',
        description: str = "I am a tool agent that can execute various tools",
    ) -> None:
        """Initialize ToolAgentWrapper
        
        Args:
            name: Agent name
            tools: List of tools to be managed by the agent
            host_address: gRPC host address
            description: Agent description
        """
        self._name = name
        self._tool_server = server
        self._host_address = host_address
        self._description = description
        
        self._runtime: Optional[GrpcWorkerAgentRuntime] = None

    async def initialize(self) -> None:
        """Initialize all components"""
        print(f"SSE Tool Agent: {self._name} is initializing")

        # Register chain identity
        membase_chain.register(self._name)
        logging.info(f"{self._name} is register onchain")
        time.sleep(3)
        
        # Initialize Runtime
        self._runtime = GrpcWorkerAgentRuntime(self._host_address)
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
        await self._runtime.start()

        try:
            await self.update_in_hub("running")
        except Exception as e:
            print(f"Error registering tool agent in hub: {e}")
        print(f"SSE Tool Agent: {self._name} is registered in hub")

        # start app
        self._app = create_starlette_app(self._tool_server._mcp_server, debug=True)
        print(f"SSE Tool Agent: {self._name} is initialized")

    async def update_in_hub(self, state: str = "running") -> None:
        """Update the agent in the hub"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        membase_url = os.getenv('MEMBASE_SSE_URL')
        if not membase_url or membase_url == "":
            raise Exception("'MEMBASE_SSE_URL' is not set")

        # content = self._description + "\n" + "\n".join([tool.name + "\n" + tool.description + "\n" + json.dumps(tool.schema["parameters"])  for tool in self._tools])
        # concat each tool info into a string
        if isinstance(self._tool_server, FastMCP):
            tools = await self._tool_server.list_tools()
            content = self._description + "\n" + "\n".join([tool.name + "\n" + tool.description + "\n" + json.dumps(tool.inputSchema)  for tool in tools])
        else:
            raise ValueError("Invalid tool server type")
    
        res = await self._runtime.send_message(
            FunctionCall(
                id=str(uuid.uuid4()),
                name="register_server",
                arguments=json.dumps({
                    "name": self._name,
                    "description": content,
                    "config": {
                        "type": "tool",
                        "url": membase_url,
                        "transport": "aip-sse",
                        "state": state,
                        "timestamp": datetime.datetime.now().isoformat()
                        }
                }),
            ),
            AgentId("config_hub", "default"),
            sender=AgentId(self._name, "default")
        )
        print(f"Response from config_hub: {res}")
        
    async def stop_when_signal(self) -> None:
        """Await the agent to stop"""
        if self._runtime:
            await self._runtime.stop_when_signal()

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        if self._runtime:
            await self.update_in_hub(state="stopped")
            await self._runtime.stop()

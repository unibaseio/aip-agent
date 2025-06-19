import base64
import uvicorn
import time

from typing import Any

from mcp.server.sse import SseServerTransport
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import Scope, Receive, Send
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager

from membase.chain.chain import membase_chain, membase_account, membase_id

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_auth(auth_header: dict[Any, Any]):
    agent_id = auth_header.get(b'x-agent')
    signature = auth_header.get(b'x-sign')
    timestamp = auth_header.get(b'x-timestamp')

    logger.debug(f"auth time: {timestamp}, agent: {agent_id}, sign: {signature}")
   
    if not signature or not timestamp or not agent_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    agent_id = agent_id.decode('utf-8')

    try:
        timestamp = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
            
    current_time = int(time.time())
    if current_time - timestamp > 300: 
        logger.warning(f"{agent_id} has expired token")
        raise HTTPException(status_code=400, detail="Token expired")

    if not membase_chain.has_auth(membase_id, agent_id):
        logger.warning(f"{agent_id} is not auth on chain")
        raise HTTPException(status_code=400, detail="No auth on chain")

    agent_address = membase_chain.get_agent(agent_id)
    signature = signature.decode('utf-8')
    verify_message = f"{timestamp}"
    if not membase_chain.valid_signature(verify_message, signature, agent_address):
        logger.warning(f"{agent_id} has invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

class BasicAuthTransport(SseServerTransport):
    def __init__(self, endpoint: str):
        super().__init__(endpoint)

    @asynccontextmanager
    async def connect_sse(self, scope: Scope, receive: Receive, send: Send):
        try:
            auth_header = dict(scope["headers"])
            verify_auth(auth_header)
        except Exception as e:
            raise e
        logger.info("sse message auth sign pass")
        async with super().connect_sse(scope, receive, send) as streams:
            yield streams

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""

    logger.info(f"start with account: {membase_account} and id: {membase_id}")
    membase_chain.register(membase_id)
    
    sse = BasicAuthTransport("/messages/")
    
    async def handle_sse(request: Request) -> None:
        try:
            auth_header = dict(request.scope["headers"])
            verify_auth(auth_header)
        except Exception as e:
            raise e
        logger.info("sse auth sign pass")
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
                server_version="0.1.5",
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
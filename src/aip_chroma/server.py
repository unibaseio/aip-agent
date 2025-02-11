import base64
import ecdsa
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

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_chroma.chroma import server

def verify_signature(message, signature, public_key):
    try:
        public_key.verify(signature, message.encode('utf-8'))
        return True
    except ecdsa.BadSignatureError:
        return False

def verify_auth(auth_header: dict[Any, Any]):
    public_key_pem_b64 = auth_header.get(b'x-publickey')
    signature = auth_header.get(b'x-sign')
    timestamp = auth_header.get(b'x-timestamp')
    logger.debug(f"auth: {timestamp} {public_key_pem_b64} {signature}")
   
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        timestamp = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
            
    current_time = int(time.time())
    if current_time - timestamp > 5: 
        raise HTTPException(status_code=400, detail="Token expired")

    verify_message = f"{timestamp}"
    public_key_pem = base64.b64decode(public_key_pem_b64)
    public_key = ecdsa.VerifyingKey.from_pem(public_key_pem)
    #todo: public key is in whitelist
    if not verify_signature(verify_message, bytes.fromhex(signature.decode('utf-8')), public_key):
        raise HTTPException(status_code=403, detail="Invalid signature")
        
    

class BasicAuthTransport(SseServerTransport):
    """
    Example basic auth implementation of SSE server transport.
    """
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
    #sse = SseServerTransport("/messages/")
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
                server_name="chroma",
                server_version="0.1.0",
                capabilities=mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                    ),
                )
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run AIP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)
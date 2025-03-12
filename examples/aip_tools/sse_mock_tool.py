
import asyncio
import uvicorn

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_agent.agents.sse_tool_agent import SSEToolAgentWrapper

from membase.chain.chain import membase_id

from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("mcp-mock-tool")

@mcp.tool()
async def calculate(a: int, b: int, ctx: Context = None) -> str:
    """calculate the sum of a and b"""
    return a + b

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run an aip sse tool.')
    parser.add_argument('--address', default='13.212.116.103:8081', help='Memabase hub address')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    
    args = parser.parse_args()

    stap = SSEToolAgentWrapper(membase_id, mcp, args.address, "this is a sse mock tool")

    asyncio.run(stap.initialize())

    print(f"SSE mock tool launched at {args.host}:{args.port}")

    uvicorn.run(stap._app, host=args.host, port=args.port)
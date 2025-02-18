
import uvicorn

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_ipinfo.server import mcp
from aip_server.server import create_starlette_app
from aip_agent_basic.client import AIPClient

async def register():
    aipc = AIPClient("agent_hub", "http://0.0.0.0:8080")

    try:
        await aipc.initialize()
    except Exception as e:
        print(e)
        await aipc.cleanup()
        raise

    tools = await mcp.list_tools()

    #tools is List[tool]
    tools_json = [tool.model_dump_json() for tool in tools]
    import json
    try:
        msgdict = json.dumps(tools_json, ensure_ascii=False)
    except Exception as e:
        msgdict = json.dumps(tools_json)
        raise e
    
    desc = "this is ipinfo server with tools: " + ", ".join([tool.name for tool in tools])
    desc = desc + ". " + msgdict
    try:
        await aipc.register(desc) 
    except Exception as e:
        print(e)

    await aipc.cleanup()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run AIP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    starlette_app = create_starlette_app(mcp._mcp_server, debug=True)

    import asyncio
    asyncio.run(register())

    uvicorn.run(starlette_app, host=args.host, port=args.port)
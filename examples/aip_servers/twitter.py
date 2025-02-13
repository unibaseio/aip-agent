
import uvicorn

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_twikit.twitter import mcp
from aip_server.server import create_starlette_app

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run AIP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()


    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp._mcp_server, debug=True)
    uvicorn.run(starlette_app, host=args.host, port=args.port)
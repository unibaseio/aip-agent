import asyncio
import time
import os
import ecdsa
import base64

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

key_path = './out/private_key.pem'
if os.path.exists(key_path):
    with open(key_path, 'rb') as f:
        private_key_pem = f.read()
        private_key = ecdsa.SigningKey.from_pem(private_key_pem)     
else:
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    private_key_pem = private_key.to_pem()
    with open(key_path, 'wb') as f:
        f.write(private_key_pem)

public_key_pem = private_key.get_verifying_key().to_pem()
public_key_pem_b64 = base64.b64encode(public_key_pem).decode('utf-8')

def sign_message(message, private_key):
    return private_key.sign(message.encode('utf-8')).hex()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        timestamp = int(time.time())
        verify_message = f"{timestamp}"
        token = sign_message(verify_message, private_key)

        headers = {
            'x-Publickey': public_key_pem_b64, 
            'x-Sign': token,
            'x-Timestamp': str(timestamp),
        }       

        self._streams_context = sse_client(url=server_url, headers=headers)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        res = await self.session.initialize()

        # List available tools to verify connection
        print(f"Initialized SSE client... {res}")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        tool_args = {
            "memory_id": "test"+str(timestamp), 
            "content": "this is test content", 
            "metadata": {
                "source": "mcp",
                "time": str(timestamp)
            }
        }
        call_res = await self.session.call_tool("create_memory", tool_args)
        print(call_res)

        #tool_args = {}
        #call_res = await self.session.call_tool("list_memorys", tool_args)
        #print(call_res)

        tool_args = {
            "query": "vector",
            'num_results': 1,
        }
        call_res = await self.session.call_tool("search_similar", tool_args)
        print(call_res)


    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URL of SSE MCP server (i.e. http://localhost:8080/sse)>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())

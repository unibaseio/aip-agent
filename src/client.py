import asyncio
import time
import os
import ecdsa
import base64

from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
    
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_chain.chain import membase_chain, membase_account, membase_id

class AIPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    def get_auth_for_test(self, server_url: str):
        logger.info(f"Get info for auth in test environment")
        import requests
        response = requests.get(server_url+"/info?agent_account="+membase_account, timeout=120)
        response.raise_for_status()
        res = response.json()
        memory_id = res['uuid']
        try:
            if not membase_chain.get_auth(memory_id, membase_id):
                logger.info(f"add agent: {membase_id} to memory: {memory_id}")
                membase_chain.add_memory(memory_id, membase_id)
        except Exception as e:
            print(e)
            exit(1)

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an AIP server running with SSE transport"""
        # Store the context managers so they stay alive
        timestamp = int(time.time())
        verify_message = f"{timestamp}"
        token = membase_chain.sign_message(verify_message)

        headers = {
            'x-Agent': membase_id, 
            'x-Sign': token,
            'x-Timestamp': str(timestamp),
        }       

        server_url = server_url + "/sse"
        self._streams_context = sse_client(url=server_url, headers=headers)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        res = await self.session.initialize()

        # List available tools to verify connection
        logger.info(f"Initialized SSE client... {res}")
        logger.info("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("Connected to server with tools:", [tool.name for tool in tools])

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

    membase_chain.register_agent(membase_id)
    logger.info(f"start agent with account: {membase_account} and id: {membase_id}")

    server_url = sys.argv[1]

    client = AIPClient()
    try:
        client.get_auth_for_test(server_url=server_url)
        await client.connect_to_sse_server(server_url=server_url)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())

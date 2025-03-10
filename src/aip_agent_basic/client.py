import asyncio
import time
import os

from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.types import TextContent
from mcp.client.sse import sse_client
    
import logging
logger = logging.getLogger(__name__)

from membase.chain.chain import membase_chain, membase_account, membase_id

class AIPClient:
    def __init__(self, name: str,server_url: str):
        # Initialize session and client objects
        self.name = name
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.server_url = server_url
        self._session_context = None
    
    async def initialize(self) -> None:
        self.get_auth_for_test()
        await self.connect_to_sse_server()

    def get_auth_for_test(self):
        logger.info(f"Get info for auth in test environment")
        import requests
        response = requests.get(self.server_url+"/info?agent_account="+membase_account, timeout=120)
        response.raise_for_status()
        res = response.json()
        memory_id = res['uuid']
        try:
            if not membase_chain.has_auth(memory_id, membase_id):
                logger.info(f"add agent: {membase_id} to hub memory: {memory_id}")
                membase_chain.buy(memory_id, membase_id)
        except Exception as e:
            print(e)
            exit(1)

    async def connect_to_sse_server(self):
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

        server_url = self.server_url + "/sse"
        try:
            self._streams_context = sse_client(url=server_url, headers=headers)
            streams = await self._streams_context.__aenter__()

            self._session_context = ClientSession(*streams)
            self.session: ClientSession = await self._session_context.__aenter__()

            # Initialize
            self.capabilities = await self.session.initialize()

            # List available tools to verify connection
            logger.info(f"Initialized SSE client... {self.capabilities}")
        except Exception as e:
            logging.error(f"Error connecting to server {self.name}: {e}")
            await self.cleanup()
            raise
        
        logger.info("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("Connected to server with tools:", [tool.name for tool in tools])

    async def register(self, desc: str):
        membase_url = os.getenv('MEMBASE_SSE_URL')
        if not membase_url or membase_url == "":
            raise Exception("'MEMBASE_SSE_URL' is not set")

        register_args = {
            "memory_id": membase_id,
            "content": desc,
            "metadata": {
                "url": membase_url,
                "transport": "aip-sse",
                "time": str(time.time()),
                "owner": membase_account,
            }
        }

        try: 
            tool_args = {"memory_id": membase_id}
            res = await self.execute_tool("read_memory", tool_args)
            print(f"res: {res}")
            contains_not_found = any(
                isinstance(item, TextContent) and 'not found' in item.text
                for item in res.content
                )
            print(contains_not_found)
            if contains_not_found:
                res = await self.execute_tool("create_memory", register_args)
                print(f"create res: {res}")
            else:
                res = await self.execute_tool("update_memory", register_args)
                print(f"update res: {res}")
        except Exception as e:
            print(f"create exc: {e}")
            raise 



    async def list_tools(self) -> List[Any]:
        """List available tools from the server.
        
        Returns:
            A list of available tools.
            
        Raises:
            RuntimeError: If the server is not initialized.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")
        
        tools_response = await self.session.list_tools()
        tools = []
        
        supports_progress = (
            self.capabilities 
            and 'progress' in self.capabilities
        )
        
        if supports_progress:
            logging.info(f"Server {self.name} supports progress tracking")
        
        for item in tools_response:
            if isinstance(item, tuple) and item[0] == 'tools':
                for tool in item[1]:
                    tools.append(Tool(tool.name, tool.description, tool.inputSchema))
                    if supports_progress:
                        logging.info(f"Tool '{tool.name}' will support progress tracking")
        
        return tools

    async def execute_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        retries: int = 2, 
        delay: float = 1.0
    ) -> Any:
        """Execute a tool with retry mechanism.
        
        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            retries: Number of retry attempts.
            delay: Delay between retries in seconds.
            
        Returns:
            Tool execution result.
            
        Raises:
            RuntimeError: If server is not initialized.
            Exception: If tool execution fails after all retries.
        """
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        while attempt < retries:
            try:
                supports_progress = (
                    self.capabilities 
                    and 'progress' in self.capabilities
                )

                if supports_progress:
                    logging.info(f"Executing {tool_name} with progress tracking...")
                    result = await self.session.call_tool(
                        tool_name, 
                        arguments,
                        progress_token=f"{tool_name}_execution"
                    )
                else:
                    logging.info(f"Executing {tool_name}...")
                    result = await self.session.call_tool(tool_name, arguments)

                return result

            except Exception as e:
                attempt += 1
                logging.warning(f"Error executing tool: {e}. Attempt {attempt} of {retries}.")
                if attempt < retries:
                    logging.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("Max retries reached. Failing.")
                    raise


    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            try:
                if self.session:
                    try:
                        await self.session.__aexit__(None, None, None)
                    except Exception as e:
                        logging.warning(f"Warning during session cleanup for {self.name}: {e}")
                    finally:
                        self.session = None

                if self._session_context:
                    try:
                        await self._session_context.__aexit__(None, None, None)
                    except (RuntimeError, asyncio.CancelledError) as e:
                        logging.info(f"Note: Normal shutdown message for {self.name}: {e}")
                    except Exception as e:
                        logging.warning(f"Warning during session context cleanup for {self.name}: {e}")
                    finally:
                        self._session_context = None

                if self._streams_context:
                    try:
                        await self._streams_context.__aexit__(None, None, None)
                    except (RuntimeError, asyncio.CancelledError) as e:
                        logging.info(f"Note: Normal shutdown message for {self.name}: {e}")
                    except Exception as e:
                        logging.warning(f"Warning during stream context cleanup for {self.name}: {e}")
                    finally:
                        self._streams_context = None
            except Exception as e:
                logging.error(f"Error during cleanup of server {self.name}: {e}")

class Tool:
    """Represents a tool with its properties and formatting."""

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]) -> None:
        self.name: str = name
        self.description: str = description
        self.input_schema: Dict[str, Any] = input_schema

    def format_for_llm(self) -> str:
        """Format tool information for LLM.
        
        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        if 'properties' in self.input_schema:
            for param_name, param_info in self.input_schema['properties'].items():
                arg_desc = f"- {param_name}: {param_info.get('description', 'No description')}"
                if param_name in self.input_schema.get('required', []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)
        
        return f"""
Tool: {self.name}
Description: {self.description}
Arguments:
{chr(10).join(args_desc)}
"""

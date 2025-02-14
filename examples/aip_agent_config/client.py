import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp_agent.app import MCPApp
from mcp_agent.mcp.mcp_aggregator import MCPAggregator
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = MCPApp(name="mcp_agent")

agg = MCPAggregator(server_names=["chroma"], connection_persistence=True)

async def list_servers():
    res = await agg.list_servers()
    print(res)
    return res

async def list_tools_of_server(server_name: str):
    res = await agg.list_tool(server_name)
    print(res)
    return res

async def list_all_tools():
    res = await agg.list_tools()
    print(res)
    return res

async def add_server(server_name: str, url: str):
    try:
        res = await agg.load_server(server_name, url)
        print(res)
    except Exception as e:
        print(e)
        raise
    return res

agent = Agent(
            name="agent",
            instruction="you are an assistant",
            server_names=["chroma"],
            mcp_aggregator=agg,
            functions=[list_servers, list_all_tools,list_tools_of_server, add_server]
        )

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def initialize(self):
        
        self.app = app
        await self.app.initialize()

        self.agent = agent
        await self.agent.initialize()

        #await add_server("twitter", "http://0.0.0.0:8081")

        #tools = await list_all_tools()
        #print(tools)

        #tools = await list_tools_of_server("chroma")
        #print(tools)

        self.llm = await self.agent.attach_llm(OpenAIAugmentedLLM)

    async def process_query(self, query: str) -> str:
        """Process a query"""
        response = await self.llm.generate_str(message=query)
        return response

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nAIP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

from aip_chain.chain import membase_chain, membase_account, membase_id
membase_chain.register(membase_id)
print(f"start agent with account: {membase_account} and id: {membase_id}")

async def main():
    client = MCPClient()
    try:
        await client.initialize()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())

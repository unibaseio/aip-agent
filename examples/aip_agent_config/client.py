import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from aip_agent.app import MCPApp
from aip_agent.agents.agent import Agent
from aip_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM

from aip_agent.memory.message import Message
from aip_agent.memory.buffered_memory import BufferedMemory

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env


import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from aip_agent.chain.chain import membase_chain, membase_account, membase_id
membase_chain.register(membase_id)
print(f"start agent with account: {membase_account} and id: {membase_id}")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.memory = BufferedMemory(persistence_in_remote=True)

    async def initialize(self):
        app = MCPApp(name="aip_app")

        agent = Agent(
            name="aip_agent",
            instruction="you are an assistant",
            server_names=["agent_hub"],
        )
        
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
        msg = Message(membase_id, query, role="user")
        self.memory.add(msg)
        response = await self.llm.generate_str(message=query)
        msg = Message(membase_id, response, role="user")
        self.memory.add(msg)
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

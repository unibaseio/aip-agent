import asyncio
from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.memory.message import Message

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from membase.chain.chain import membase_chain, membase_account, membase_id
membase_chain.register(membase_id)
print(f"start agent with account: {membase_account} and id: {membase_id}")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.full_agent = FullAgentWrapper(
            agent_cls=CallbackAgent,
            name=membase_id,
            description="you are an assistant",
        )

    async def initialize(self):
        await self.full_agent.initialize()

    async def process_query(self, query: str) -> str:
        """Process a query"""
        msg = Message(membase_id, query, role="user")
        self.full_agent._memory.add(msg)
        response = await self.full_agent._llm.generate_str(message=query)
        msg = Message(membase_id, response, role="user")
        self.full_agent._memory.add(msg)
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
        await self.full_agent.stop()

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

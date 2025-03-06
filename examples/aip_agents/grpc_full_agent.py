import argparse
import asyncio
import logging

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id
from membase.memory.message import Message

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())

async def main(address: str) -> None:
    """Main Entrypoint."""

    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,
        name=membase_id,
        description="You are an assistant",
        host_address=address,
    )
    await full_agent.initialize()

    servers = await full_agent._mcp_agent.list_servers()
    print(f"servers: {servers}")

    tools = await full_agent._mcp_agent.list_tools()
    print(f"tools: {tools}")

    while True:
        try:
            query = await async_input("\nQuery: ")

            if query.lower() == "quit":
                break
            
            full_agent._memory.add(Message(content=query, name=membase_id, role="user"))
            response = await full_agent._llm.generate_str(query)
            full_agent._memory.add(Message(content=response, name=membase_id, role="assistant"))
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")

    await full_agent.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="localhost:50060")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address))

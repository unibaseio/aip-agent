import argparse
import asyncio
import logging

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent

from membase.chain.chain import membase_id

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
        server_names=["membase"],
    )
    await full_agent.initialize()

    #await full_agent.load_server("weather_mock_server", "grpc")

    servers = await full_agent._mcp_agent.list_servers()
    print(f"servers: {servers}")

    tools = await full_agent._mcp_agent.list_tools()
    print(f"tools: {tools}")


    while True:
        try:
            query = await async_input("\nQuery: ")

            if query.lower() == "quit":
                break
            
            response = await full_agent.process_query(query)
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")

    await full_agent.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="54.169.29.193:8081")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("aip_agent").setLevel(logging.DEBUG)
        logging.getLogger("autogen").setLevel(logging.DEBUG)

    asyncio.run(main(args.address))

import argparse
import asyncio

from aip_agent.grpc import GrpcWorkerAgentRuntimeHost
from rich.console import Console
from rich.markdown import Markdown


async def main(address: str):
    host = GrpcWorkerAgentRuntimeHost(address=address)
    host.start()

    console = Console()
    console.print(
        Markdown(f"**`Membase Hub`** is now running and listening for connection at **`{address}`**")
    )
    await host.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run membase hub for agent communication.")
    parser.add_argument("--address", type=str, help="Address to listen on", default="localhost:50060")
    args = parser.parse_args()
    asyncio.run(main(args.address))

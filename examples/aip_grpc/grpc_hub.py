import asyncio

from aip_agent.grpc import GrpcWorkerAgentRuntimeHost
from rich.console import Console
from rich.markdown import Markdown


async def main():
    address = 'localhost:50060'
    host = GrpcWorkerAgentRuntimeHost(address=address)
    host.start()

    console = Console()
    console.print(
        Markdown(f"**`Membase Hub`** is now running and listening for connection at **`{address}`**")
    )
    await host.stop_when_signal()


if __name__ == "__main__":
    asyncio.run(main())

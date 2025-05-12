import argparse
import asyncio
import datetime
import logging
import os
import random
from typing import Annotated, List

from autogen_core.tools import FunctionTool, Tool

from aip_agent.agents.tool_agent import ToolAgentWrapper

from membase.chain.chain import membase_id

def get_weather(
    city: Annotated[str, "The city name"],
    date: Annotated[str, "The date"],
) -> str:
    weather = random.choice(["sunny", "cloudy", "rainy", "snowy"])
    return weather + " in " + city + " on " + date


def get_date() -> str:
    return datetime.datetime.now().isoformat()

async def main(address: str) -> None:
    local_tools: List[Tool] = [
        FunctionTool(
            get_weather,
            name="get_weather",
            description="Get the weather of a city on a specific date.",
        ),
        FunctionTool(
            get_date,
            name="get_date",
            description="Get the current date.",
        ),
    ]
    
    tool_agent = ToolAgentWrapper(
        name=os.getenv("MEMBASE_ID"),
        tools=local_tools,
        host_address=address,
        description="This is a tool agent that can get the weather of a city on a specific date and get the current date."
    )
    await tool_agent.initialize()
    print(f"GRPC mock tool launched as {membase_id} at {address}")
    await tool_agent.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an aip grpc tool.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="Address to connect to", default="54.169.29.193:8081")
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)

    asyncio.run(main(args.address))

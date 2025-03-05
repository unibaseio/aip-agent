import argparse
import asyncio
import logging
import os
import random
import time
import yaml
from typing import Annotated, Any, Dict, List, Literal

from autogen_core import (
    AgentRuntime,
    FunctionCall,
    try_get_known_serializers_for_type,
    message_handler,
)

from autogen_core.models import (
    FunctionExecutionResult,
)
from autogen_core.tools import FunctionTool, Tool, ToolSchema

from aip_agent.agents.tool_agent import ToolAgentWrapper

from aip_agent.message.message import InteractionMessage
from membase.chain.chain import membase_id


def get_legal_moves(role_type: Annotated[str, "Role type: white or black"]) -> str:
    movers = random.choice(["pawn", "knight", "bishop", "rook", "queen", "king"])
    return movers + " moves to " + random.choice(["a1", "b2", "c3", "d4", "e5", "f6", "g7", "h8"])

def get_weather(
    city: Annotated[str, "The city name"],
    date: Annotated[str, "The date"],
) -> str:
    weather = random.choice(["sunny", "cloudy", "rainy", "snowy"])
    return weather + " in " + city + " on " + date

def get_board() -> Annotated[str, "The current board state"]:
    return "board is " + random.choice(["empty", "white", "black"])

async def main(address: str) -> None:
    local_tools: List[Tool] = [
        FunctionTool(
            get_legal_moves,
            name="get_legal_moves",
            description="Get legal moves.",
        ),
        FunctionTool(
            get_weather,
            name="get_weather",
            description="Get the weather of a city on a specific date.",
        ),
        FunctionTool(
            get_board,
            name="get_board",
            description="Get the current board state.",
        ),
    ]

    
    tool_agent = ToolAgentWrapper(
        name=os.getenv("MEMBASE_ID"),
        tools=local_tools,
        host_address=address,
    )
    await tool_agent.initialize()
    await tool_agent.stop_when_signal()


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

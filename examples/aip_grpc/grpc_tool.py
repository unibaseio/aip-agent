import argparse
import asyncio
import logging
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

from aip_agent.grpc import GrpcWorkerAgentRuntime


from aip_agent.tool_agent import ToolAgent
from aip_agent.message.message import InteractionMessage
from membase.chain.chain import membase_chain, membase_id


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

async def main() -> None:
    membase_chain.register(membase_id)
    print(f"{membase_id} is register onchain")
    time.sleep(5)

    runtime = GrpcWorkerAgentRuntime('localhost:50060')
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
    runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
    await runtime.start()

    chess_tools: List[Tool] = [
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

    await ToolAgent.register(
        runtime,
        membase_id,
        lambda: ToolAgent(description="Tool agent for test.", tools=chess_tools),
    )
    
    await runtime.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "tool.log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main())

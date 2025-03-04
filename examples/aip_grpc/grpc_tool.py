import argparse
import asyncio
import logging
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

async def board_tool(runtime: AgentRuntime) -> None:  # type: ignore
    def get_legal_moves(role_type: Annotated[str, "Role type: white or black"]) -> str:
        return role_type

    def make_move(
        role_type: Annotated[str, "Role type: white or black"],
        move: Annotated[str, "A move in UCI format"],
    ) -> str:
        return role_type+move

    def get_board() -> Annotated[str, "The current board state"]:
        return "board"

    chess_tools: List[Tool] = [
        FunctionTool(
            get_legal_moves,
            name="get_legal_moves",
            description="Get legal moves.",
        ),
        FunctionTool(
            make_move,
            name="make_move",
            description="Make a move.",
        ),
        FunctionTool(
            get_board,
            name="get_board",
            description="Get the current board state.",
        ),
    ]

    # Register the agents.
    tool_agent_type = membase_id
    await ToolAgent.register(
        runtime,
        tool_agent_type,
        lambda: ToolAgent(description="Tool agent for chess game.", tools=chess_tools),
    )


async def main() -> None:
    """Main Entrypoint."""

    membase_chain.register(membase_id)
    print(f"{membase_id} is register onchain")
    time.sleep(5)

    runtime = GrpcWorkerAgentRuntime('localhost:50060')
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
    runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
    await runtime.start()

    await board_tool(runtime)
    
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

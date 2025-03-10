# role agent for wolf, village, seer, witch

import argparse
import asyncio
import time
import yaml
import logging
from typing import Any, Dict, List

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    message_handler,
)

from membase.memory.message import Message
from membase.memory.multi_memory import MultiMemory
from membase.chain.chain import membase_chain, membase_id

from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.workflows.llm.augmented_llm import AugmentedLLM
from aip_agent.message.message import InteractionMessage
from prompt import get_game_prompt

class PlayerAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        llm: AugmentedLLM,
        memory: MultiMemory,
        role_type: str,
    ) -> None:
        super().__init__(description=description)
        self._llm = llm
        self._memory = memory
        self._role_type = role_type
        print(f"=== start agent: {self.id}")
        
    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        """Handle incoming messages based on their type."""

        print(message)

        msg = Message(content=message.content, role="user", name=message.source)
        self._memory.add(msg)

        input_messages = get_game_prompt(self._role_type) + "\n" + message.content
        
        # Get LLM response
        response = await self._llm.generate_str(input_messages)

        print(response)

        # Add response to memory and return
        self._memory.add(Message(content=response, role="assistant", name=self.id.type))
        return InteractionMessage(action="response", content=response, source=self.id.type)


import os
membase_task_id = os.getenv('MEMBASE_TASK_ID')
if not membase_task_id or membase_task_id == "":
    print("'MEMBASE_TASK_ID' is not set, user defined")
    raise Exception("'MEMBASE_TASK_ID' is not set, user defined")

async def main(address: str, moderator_id: str, role_type: str) -> None:
    membase_chain.register(membase_id)
    print(f"{membase_id} is register onchain")
    time.sleep(3)

    membase_chain.joinTask(membase_task_id, membase_id)
    print(f"{membase_id} join task {membase_task_id} onchain")
    time.sleep(3)
    
    # start the game
    fa = FullAgentWrapper(
        agent_cls=PlayerAgent,
        name=membase_id,
        host_address=address,
        description="You are player in chess game",
        role_type=role_type,
    )
    await fa.initialize()

    print(f"=== send register message to {moderator_id} {role_type}")
    role_msg = await fa._runtime.send_message(
        InteractionMessage(action="register",content=role_type, source=membase_id),
        AgentId(moderator_id, membase_task_id),
        sender=AgentId(membase_id, membase_task_id)
    )
    print(f"=== register message receive from {moderator_id} {role_msg}")

    if role_msg.content == "":
        print("=== role is not accepted, exit")
        fa.stop()
        return
    
    await fa.stop_when_signal()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--address", type=str, help="address to connect to", default="13.212.116.103:8081")
    parser.add_argument(
        "--moderator", type=str, help="moderator id", default="board_starter"
    )
    parser.add_argument(
        "--role", type=str, help="role type", default=""
    )

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "chess_game_" + membase_id + ".log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args.address, args.moderator, args.role))
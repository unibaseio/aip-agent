import argparse
import asyncio
import json
import logging
import time
import yaml
from typing import Annotated, Any, Dict, List, Literal

from autogen_core import (
    AgentId,
    FunctionCall,
    MessageContext,
    RoutedAgent,
    message_handler,
    try_get_known_serializers_for_type,
)

from autogen_core.models import (
    FunctionExecutionResult,
)

from aip_agent.agents.agent import Agent
from aip_agent.app import MCPApp
from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.workflows.llm.augmented_llm import AugmentedLLM
from aip_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM

from pydantic import BaseModel


from aip_agent.tool_agent import InteractionMessage
from membase.chain.chain import membase_chain, membase_id
from membase.memory.buffered_memory import BufferedMemory
from membase.memory.message import Message
from membase.memory.memory import MemoryBase

class PlayerAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        model_client: AugmentedLLM,
        memory: MemoryBase,
    ) -> None:
        super().__init__(description=description)

        self._memory = memory
        self._model_client = model_client
        print(f"=== start agent: {self.id}")

    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        self._memory.add(Message(content=message.content, name=message.source, role="user"))
        try:
            response = await self._model_client.generate_str(message.content)
        except Exception as e:
            print(f"Error: {e}")
            response = "I'm sorry, I couldn't generate a response to that message."
        self._memory.add(Message(content=response, name=self.id, role="assistant"))
        return InteractionMessage(
            action="response",
            content=response,
            source=self.id.type
        )

async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt).strip())

async def main(tool_id: str) -> None:
    """Main Entrypoint."""

    membase_chain.register(membase_id)
    print(f"{membase_id} is register onchain")
    time.sleep(5)

    runtime = GrpcWorkerAgentRuntime('localhost:50060')
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
    runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
    await runtime.start()

    response = await runtime.send_message(
        InteractionMessage(
            action="list_tools",
        ),
        AgentId(tool_id, "tool"),
        sender=AgentId(membase_id, "tool"))
    print(f"response: {response.content}")

    response = await runtime.send_message(
        FunctionCall(
            name="get_board",
            arguments=json.dumps({}),
            id="1"
        ),
        AgentId(tool_id, "tool"),
        sender=AgentId(membase_id, "tool")
    )
    print(f"response: {response}")

    app = MCPApp(name=membase_id)

    agent = Agent(
        name=membase_id,
        runtime=runtime,
        instruction="you are an assistant",
    )
        
    await app.initialize()
    await agent.initialize()
    
    await agent.load_server(server_name = tool_id, url="aip-grpc")

    servers = await agent.list_servers()
    print(f"servers: {servers}")

    tools = await agent.list_tools()
    print(f"tools: {tools}")

    result = await agent.call_tool(name="get_board", arguments={})
    print(f"result: {result}")


    llm = await agent.attach_llm(OpenAIAugmentedLLM)

    memory = BufferedMemory(persistence_in_remote=True)

    await PlayerAgent.register(
        runtime,
        membase_id,
        lambda: PlayerAgent(
            description=f"You are an assistant",
            model_client=llm,
            memory=memory
        ),
    )

    while True:
        try:
            query = await async_input("\nQuery: ")

            if query.lower() == "quit":
                break
            
            memory.add(Message(content=query, name=membase_id, role="user"))
            response = await llm.generate_str(query)
            memory.add(Message(content=response, name=membase_id, role="assistant"))
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")

    await runtime.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--tool", type=str, help="Tool ID")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("grpc").setLevel(logging.DEBUG)
        file_name = "agent.log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("grpc").addHandler(handler)

    asyncio.run(main(args.tool))

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
    ChatCompletionClient,
    UserMessage
)

from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.message.message import InteractionMessage

from membase.chain.chain import membase_chain, membase_id, membase_account
from membase.memory.buffered_memory import BufferedMemory
from membase.memory.message import Message
from membase.memory.memory import MemoryBase

class PlayerAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        memory: MemoryBase,
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description=description)
        self._memory = memory
        self._model_client = model_client
        print(f"=== start agent1: {self.id}")

    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        self._memory.add(Message(content=message.content, name=message.source, role="user"))
        user_message = UserMessage(content=message.content, source=message.source)
        response = await self._model_client.create([user_message])
        self._memory.add(Message(content=response.content, name=self.id, role="assistant"))
        return InteractionMessage(
            action="response",
            content=response.content,
            source=self.id.type
        )

async def main(model_config: Dict[str, Any]) -> None:
    """Main Entrypoint."""

    membase_chain.register(membase_id)
    print(f"{membase_id} is register onchain")
    time.sleep(5)

    runtime = GrpcWorkerAgentRuntime('localhost:50060')
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
    runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
    runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
    await runtime.start()

    memory = BufferedMemory(membase_account=membase_account, auto_upload_to_hub=True)


    model_client = ChatCompletionClient.load_component(model_config)

    await PlayerAgent.register(
        runtime,
        membase_id,
        lambda: PlayerAgent(
            description=f"You are an assistant",
            memory=memory,
            model_client=model_client,
        ),
    )

    res = await runtime.send_message(
        InteractionMessage(
            action="ask",
            content="hello",
            source=membase_id
        ),
        AgentId("test", "default"),
        sender=AgentId(membase_id, "default")
    )
    print(f"res: {res}")

    await runtime.stop_when_signal()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a chess game between two agents.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    parser.add_argument(
        "--model-config", type=str, help="Path to the model configuration file.", default="model_config.yml"
    )

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "grcp_server.log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)
    
    with open(args.model_config, "r") as f:
        model_config = yaml.safe_load(f)

    asyncio.run(main(model_config))

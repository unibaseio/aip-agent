import argparse
import asyncio
import json
import logging
import time
from typing import Optional, Type, TypeVar

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

from aip_agent.tool_agent import InteractionMessage
from membase.chain.chain import membase_chain, name, membase_account
from membase.memory.buffered_memory import BufferedMemory
from membase.memory.message import Message
from membase.memory.memory import MemoryBase

T = TypeVar('T', bound=RoutedAgent)

class AIAgent:
    """A wrapper class that manages different types of RoutedAgents with common infrastructure"""
    
    def __init__(
        self,
        agent_cls: Type[T],
        name: str,
        host_address: str = 'localhost:50060',
        description: str = "You are an assistant",
        **agent_kwargs
    ) -> None:
        """Initialize AIAgent
        
        Args:
            agent_cls: The RoutedAgent class to instantiate
            name: Agent name
            host_address: gRPC host address
            description: Agent description
            agent_kwargs: Additional arguments to pass to the agent class
        """
        self._agent_cls = agent_cls
        self._name = name
        self._host_address = host_address
        self._description = description
        self._agent_kwargs = agent_kwargs
        
        self._runtime: Optional[GrpcWorkerAgentRuntime] = None
        self._app: Optional[MCPApp] = None
        self._llm: Optional[AugmentedLLM] = None
        self._memory: Optional[BufferedMemory] = None
        self._agent: Optional[T] = None

    async def initialize(self) -> None:
        """Initialize all components"""
        # Register chain identity
        membase_chain.register(self._name)
        print(f"{self._name} is register onchain")
        
        # Initialize Runtime
        self._runtime = GrpcWorkerAgentRuntime(self._host_address)
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
        await self._runtime.start()
        
        # Initialize Memory
        self._memory = BufferedMemory(membase_account=membase_account, auto_upload_to_hub=True)
        
        # Initialize LLM
        self._llm = await self._init_llm()
        
        # Initialize Agent
        self._agent = self._agent_cls(
            description=self._description,
            **self._agent_kwargs
        )
        
        # Register Agent
        await self.register_agent()

    async def _init_llm(self) -> AugmentedLLM:
        """Initialize LLM model"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        self._app = MCPApp(name=self._name)
        await self._app.initialize()

        agent = Agent(
            name=self._name,
            runtime=self._runtime,
            instruction="you are an assistant",
        )
        await agent.initialize()
        return await agent.attach_llm(OpenAIAugmentedLLM)

    async def register_agent(self) -> None:
        """Register the agent with the runtime"""
        if not self._runtime or not self._llm or not self._memory or not self._agent:
            raise RuntimeError("Components not initialized")
            
        await self._agent_cls.register(
            self._runtime,
            self._name,
            lambda: self._agent_cls(
                description=self._description,
                **self._agent_kwargs
            )
        )

    async def process_query(self, query: str) -> str:
        """Process user queries and generate responses"""
        if not self._memory or not self._llm:
            raise RuntimeError("Components not initialized")
            
        self._memory.add(Message(content=query, name=self._name, role="user"))
        response = await self._llm.generate_str(query)
        self._memory.add(Message(content=response, name=self._name, role="assistant"))
        return response

    async def send_message(self, target_id: str, message: str) -> str:
        """Send a message to a target agent"""
        if not self._runtime or not self._agent:
            raise RuntimeError("Components not initialized")
            
        response = await self._runtime.send_message(
            InteractionMessage(
                action="ask",
                content=message,
                source=self._agent.id.type
            ),
            AgentId(target_id, "default"),
            sender=AgentId(self._agent.id.type, "default")
        )
        print(f"Response from {target_id}: {response.content}")
        return response.content

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        if self._runtime:
            await self._runtime.stop()

# Example of a custom RoutedAgent implementation
class CustomAgent(RoutedAgent):
    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        return InteractionMessage(
            action="response",
            content=f"Custom agent received: {message.content}",
            source=self.id.type
        )

# Usage example
async def main() -> None:
    # Create and initialize agent with CustomAgent
    agent = AIAgent(
        agent_cls=CustomAgent,
        name="custom_agent",
        description="I am a custom agent",
        # Additional kwargs for CustomAgent if needed
        custom_param="value"
    )
    await agent.initialize()
    
    # Use the agent
    response = await agent.process_query("Hello!")
    print(response)
    
    # Stop agent
    await agent.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI Agent")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        file_name = "agent.log"
        handler = logging.FileHandler(file_name)
        logging.getLogger("autogen_core").addHandler(handler)
    
    asyncio.run(main())

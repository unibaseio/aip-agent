import logging
import time
from typing import Optional, Type, TypeVar, Union, List

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

from aip_agent.message.message import InteractionMessage
from membase.chain.chain import membase_chain, membase_account
from membase.memory.buffered_memory import BufferedMemory
from membase.memory.message import Message
from membase.memory.memory import MemoryBase

T = TypeVar('T', bound=RoutedAgent)

class FullAgentWrapper:
    """A wrapper class that manages different types of RoutedAgents with common infrastructure"""
    
    def __init__(
        self,
        agent_cls: Type[T],
        name: str,
        host_address: str = 'localhost:50060',
        description: str = "You are an assistant",
        server_names: List[str] = None,
        **agent_kwargs
    ) -> None:
        """Initialize FullAgent
        
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
        self._server_names = server_names
        self._runtime: Optional[GrpcWorkerAgentRuntime] = None
        self._app: Optional[MCPApp] = None
        self._llm: Optional[AugmentedLLM] = None
        self._memory: Optional[BufferedMemory] = None
        self._mcp_agent: Optional[Agent] = None
        self._agent: Optional[T] = None

    async def initialize(self) -> None:
        """Initialize all components"""
        print(f"Full Agent {self._name} is initializing")
        # Register chain identity
        membase_chain.register(self._name)
        logging.info(f"{self._name} is register onchain")
        time.sleep(3)
        
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
        
        # Register Agent
        await self.register_agent()
        print(f"Full Agent {self._name} is initialized")

    async def _init_llm(self) -> AugmentedLLM:
        """Initialize LLM model"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        self._app = MCPApp(name=self._name)
        await self._app.initialize()

        self._mcp_agent = Agent(
            name=self._name,
            runtime=self._runtime,
            instruction="you are an assistant",
            server_names=self._server_names,
        )
        await self._mcp_agent.initialize()
        return await self._mcp_agent.attach_llm(OpenAIAugmentedLLM)

    async def register_agent(self) -> None:
        """Register the agent with the runtime"""
        if not self._runtime or not self._llm or not self._memory:
            raise RuntimeError("Components not initialized")
            
        # Initialize and register agent  
        await self._agent_cls.register(
            self._runtime,
            self._name,
            lambda: self._agent_cls(
                description=self._description,
                llm=self._llm,
                memory=self._memory,
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

    async def send_message(self, target_id: str, action: str, message: str):
        """Send a message to a target agent"""
        if not self._runtime:
            raise RuntimeError("Components not initialized")
            
        response = await self._runtime.send_message(
            InteractionMessage(
                action=action,
                content=message,
                source=self._name
            ),
            AgentId(target_id, "default"),
            sender=AgentId(self._name, "default")
        )
        print(f"Response from {target_id}: {response.content}")
        return response

    async def stop_when_signal(self) -> None:
        """Wait for the agent to stop"""
        if self._runtime:
            await self._runtime.stop_when_signal()

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        if self._runtime:
            await self._runtime.stop()

class CustomAgent(RoutedAgent):
    def __init__(
        self,
        description: str,
        llm: AugmentedLLM,
        memory: MemoryBase,
    ) -> None:
        super().__init__(description=description)
        self._memory = memory
        self._llm = llm

    @message_handler
    async def handle_message(self, message: InteractionMessage, ctx: MessageContext) -> InteractionMessage:
        self._memory.add(Message(content=message.content, name=message.source, role="user"))
        try:
            response = await self._llm.generate_str(message.content)
        except Exception as e:
            response = "I'm sorry, I couldn't generate a response to that message."
        self._memory.add(Message(content=response, name=self.id, role="assistant"))
        return InteractionMessage(
            action="response",
            content=response,
            source=self.id.type
        )


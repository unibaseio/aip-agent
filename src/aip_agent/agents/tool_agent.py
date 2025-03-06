import datetime
import json
import logging
import time
from typing import Optional, List
import uuid
from autogen_core import (
    AgentId,
    try_get_known_serializers_for_type,
)

from autogen_core.tools import Tool

from aip_agent.tool_agent import ToolAgent
from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.message.message import InteractionMessage, FunctionCall, FunctionExecutionResult
from membase.chain.chain import membase_chain

class ToolAgentWrapper:
    """A wrapper class that manages ToolAgent with common infrastructure"""
    
    def __init__(
        self,
        name: str,
        tools: List[Tool],
        host_address: str = '13.212.116.103:8081',
        description: str = "I am a tool agent that can execute various tools",
    ) -> None:
        """Initialize ToolAgentWrapper
        
        Args:
            name: Agent name
            tools: List of tools to be managed by the agent
            host_address: gRPC host address
            description: Agent description
        """
        self._name = name
        self._tools = tools
        self._host_address = host_address
        self._description = description
        
        self._runtime: Optional[GrpcWorkerAgentRuntime] = None

    async def initialize(self) -> None:
        """Initialize all components"""
        print(f"Tool Agent {self._name} is initializing")

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

        # Register Agent
        await self.register_agent()
        print(f"Tool Agent: {self._name} is initialized")
        try:
            await self.update_in_hub("running")
        except Exception as e:
            print(f"Error registering tool agent in hub: {e}")
        print(f"Tool Agent: {self._name} is registered in hub")

    async def register_agent(self) -> None:
        """Register the agent with the runtime"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
            
        # Initialize and register agent  
        await ToolAgent.register(
            self._runtime,
            self._name,
            lambda: ToolAgent(
                description=self._description,
                tools=self._tools
            )
        )

    async def update_in_hub(self, state: str = "running") -> None:
        """Update the agent in the hub"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        # concat each tool info into a string
        content = self._description + "\n" + "\n".join([tool.name + "\n" + tool.description + "\n" + json.dumps(tool.schema["parameters"])  for tool in self._tools])
        
        res = await self._runtime.send_message(
            FunctionCall(
                id=str(uuid.uuid4()),
                name="register_server",
                arguments=json.dumps({
                    "name": self._name,
                    "description": content,
                    "config": {
                        "type": "tool",
                        "transport": "aip-grpc",
                        "state": state,
                        "timestamp": datetime.datetime.now().isoformat()
                        }
                }),
            ),
            AgentId("config_hub", "default"),
            sender=AgentId(self._name, "default")
        )
        print(f"Response from config_hub: {res}")
        
    async def stop_when_signal(self) -> None:
        """Await the agent to stop"""
        if self._runtime:
            await self._runtime.stop_when_signal()

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        if self._runtime:
            await self.update_in_hub(state="stopped")
            await self._runtime.stop()

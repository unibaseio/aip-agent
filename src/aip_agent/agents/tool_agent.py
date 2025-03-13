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
import asyncio

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
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_failures = 0
        self._max_failures = 3
        self._running = True

    async def _send_heartbeat(self) -> None:
        """Send heartbeat message to self periodically"""
        while self._running:
            try:
                if not self._runtime:
                    raise RuntimeError("Runtime not initialized")
                
                # use asyncio.wait_for to add timeout mechanism
                try:
                    await asyncio.wait_for(
                        self._runtime.send_message(
                            InteractionMessage(
                                action="heartbeat",
                                content="ok",
                                source=self._name
                            ),
                            AgentId(self._name, "default"),
                            sender=AgentId(self._name, "default")
                        ),
                        timeout=10.0  # 10 seconds timeout
                    )
                    self._heartbeat_failures = 0
                except asyncio.TimeoutError:
                    print("Heartbeat message timed out after 10 seconds")
                    self._heartbeat_failures += 1
                    if self._heartbeat_failures >= self._max_failures:
                        print(f"Too many heartbeat failures ({self._heartbeat_failures}), stopping agent")
                        await self.stop()
                        break
                    await asyncio.sleep(30*self._heartbeat_failures)  # wait 5 seconds and retry
                    continue
                
                await asyncio.sleep(60)  # wait 60 seconds and send heartbeat again
            except Exception as e:
                print(f"Heartbeat failed: {e}")
                self._heartbeat_failures += 1
                if self._heartbeat_failures >= self._max_failures:
                    print(f"Too many heartbeat failures ({self._heartbeat_failures}), stopping agent")
                    await self.stop()
                    break
                await asyncio.sleep(30*self._heartbeat_failures)  # wait 5 seconds and retry

    async def initialize(self) -> None:
        """Initialize all components"""
        print(f"Tool Agent: {self._name} is initializing")

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
        
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._send_heartbeat())
        
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
        
        try:
            res = await asyncio.wait_for(
                self._runtime.send_message(
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
                ),
                timeout=10.0  # 10 seconds timeout
            )
            print(f"Response from config_hub: {res}")
        except asyncio.TimeoutError:
            print("Update in hub timed out after 10 seconds")
            raise
        except Exception as e:
            print(f"Error updating in hub: {e}")
            raise

    async def stop_when_signal(self) -> None:
        """Await the agent to stop"""
        if self._runtime:
            await self._runtime.stop_when_signal()

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self._runtime:
            await self.update_in_hub(state="stopped")
            await self._runtime.stop()

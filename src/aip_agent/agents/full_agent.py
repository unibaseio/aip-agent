import datetime
import json
import logging
import time
from typing import Callable, Optional, Type, TypeVar, List
import uuid
import asyncio

from autogen_core import (
    AgentId,
    RoutedAgent,
    try_get_known_serializers_for_type,
)

from aip_agent.agents.agent import Agent
from aip_agent.app import MCPApp
from aip_agent.grpc import GrpcWorkerAgentRuntime
from aip_agent.workflows.llm.augmented_llm import (
    AugmentedLLM, 
    RequestParams
)
from aip_agent.workflows.llm.augmented_llm_openai import (
    OpenAIAugmentedLLM, 
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam
)

from aip_agent.message.message import InteractionMessage, FunctionCall, FunctionExecutionResult
from membase.chain.chain import membase_chain, membase_account
from membase.memory.message import Message
from membase.memory.multi_memory import MultiMemory

T = TypeVar('T', bound=RoutedAgent)

class FullAgentWrapper:
    """A wrapper class that manages different types of RoutedAgents with common infrastructure"""
    
    def __init__(
        self,
        agent_cls: Type[T],
        name: str,
        host_address: str = '54.169.29.193:8081',
        description: str = "You are an assistant",
        runtime: Optional[GrpcWorkerAgentRuntime] = None,
        server_names: List[str] = None,
        functions: List[Callable] = None,
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
        self._server_names = server_names
        self._functions = functions
        self._agent_kwargs = agent_kwargs
        
        if runtime:
            self._runtime = runtime  
        else:
            self._runtime = GrpcWorkerAgentRuntime(self._host_address) 
        self._app: Optional[MCPApp] = None
        self._llm: Optional[AugmentedLLM] = None
        self._memory: Optional[MultiMemory] = None
        self._mcp_agent: Optional[Agent] = None
        self._initialized = False
        
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_failures = 0
        self._max_failures = 5
        self._running = True

    async def _send_heartbeat(self) -> None:
        """Send heartbeat message to self periodically"""
        while self._running:
            try:
                if not self._runtime or not self._initialized:
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
                    await asyncio.sleep(30*self._heartbeat_failures)  # wait and retry
                    continue
                
                await asyncio.sleep(60)  # wait 60 seconds and send heartbeat again
            except Exception as e:
                print(f"Heartbeat failed: {e}")
                self._heartbeat_failures += 1
                if self._heartbeat_failures >= self._max_failures:
                    print(f"Too many heartbeat failures ({self._heartbeat_failures}), stopping agent")
                    await self.stop()
                    break
                await asyncio.sleep(30*self._heartbeat_failures)  # wait and retry

    async def initialize(self) -> None:
        """Initialize all components"""
        print(f"Full Agent: {self._name} is initializing")
        # Register chain identity
        membase_chain.register(self._name)
        logging.info(f"{self._name} is register onchain")
        time.sleep(3)
        
        # Initialize Runtime
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionCall))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(FunctionExecutionResult))
        self._runtime.add_message_serializer(try_get_known_serializers_for_type(InteractionMessage))
        await self._runtime.start()
        
        # Initialize Memory
        default_conversation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, self._name))  
        self._memory = MultiMemory(
            membase_account=membase_account, 
            auto_upload_to_hub=True, 
            preload_from_hub=False,
            default_conversation_id=default_conversation_id  
        )
        self._memory.load_from_hub(default_conversation_id)
        
        # Initialize LLM
        self._llm = await self._init_llm()
        
        # Register Agent
        await self.register_agent()
        print(f"Full Agent: {self._name} is initialized")

        # Register in hub
        try:
            await self.update_in_hub("running")
            print(f"Full Agent: {self._name} is registered in hub")
        except Exception as e:
            print(f"Error registering full agent in hub: {e}")

        # Load hub servers
        try:
            await self.load_server("config_hub", "grpc")  
            await self.load_server("memory_hub", "grpc")
            print(f"Full Agent: {self._name} is connected to hub")
        except Exception as e:
            print(f"Error connecting to hub: {e}")

        self._initialized = True
        
        # Start heartbeat after initialization is complete
        self._heartbeat_task = asyncio.create_task(self._send_heartbeat())

    async def _init_llm(self) -> AugmentedLLM:
        """Initialize LLM model"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        self._app = MCPApp(name=self._name)
        await self._app.initialize()

        self._mcp_agent = Agent(
            name=self._name,
            runtime=self._runtime,
            instruction=self._description,
            server_names=self._server_names,
            functions=self._functions
        )
        await self._mcp_agent.initialize()
        return await self._mcp_agent.attach_llm(OpenAIAugmentedLLM)

    async def register_agent(self) -> None:
        """Register the agent with the runtime"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
            
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

    async def process_query(self, 
                            query: str, 
                            conversation_id: Optional[str] = None, 
                            use_history: bool = True,
                            system_prompt: Optional[str] = None,
                            recent_n_messages: int = 16,
                            ) -> str:
        """Process user queries and generate responses"""
        if not self._initialized:
            raise RuntimeError("Agent not initialized")
        
        memory = self._memory.get_memory(conversation_id)
        self._memory.load_from_hub(conversation_id) 

        # query starts with @xxx, it is a command to the xxx agent
        # "@agent_text, query" or "@agent_text query"
        if query.startswith("@"):
            memory.add(Message(content=query, name=self._name, role="user"))

            # Remove @ symbol first
            query_without_at = query[1:]

            # check if query_without_at is start with " "
            if query_without_at.startswith(" "):
                return "Error: Agent name cannot start with space. Please remove the space after @."

            if query_without_at.startswith(","):
                return "Error: Agent name cannot start with comma. Please remove the comma after @."

            # Split by first space to separate agent name and message
            parts = query_without_at.split(" ", 1)
            agent_name = parts[0].strip()
            if agent_name == "":
                return "Error: Agent name cannot be empty. Please specify an agent name after @"
            
            # check if agent name contains comma
            if "," in agent_name:
                parts = agent_name.split(",", 1)
                agent_name = parts[0].strip()
                if agent_name == "":
                    return "Error: Agent name cannot be empty. Please specify an agent name after @"
          
            new_query = query_without_at[len(agent_name)+1:]

            # remove space at beginning of new_query
            new_query = new_query.strip()

            if new_query == "":
                return "Error: Query cannot be empty. Please use '@agent_name, query' or '@agent_name query'."
            
            try:
                response = await self.send_message(agent_name, "ask", new_query)
                if response.startswith("Error:"):
                    return response
                memory.add(Message(content=response, name=agent_name, role="assistant"))
                return response
            except Exception as e:
                return f"Error: {e}"

        if use_history:
            msgs = memory.get(recent_n=recent_n_messages)
        else:
            msgs = []

        # covert msg into MessageParamT
        mps = []
        for msg in msgs:
            if msg.role == "user":
                mps.append(ChatCompletionUserMessageParam(content=msg.content, role=msg.role))
            elif msg.role == "assistant":
                mps.append(ChatCompletionAssistantMessageParam(content=msg.content, role=msg.role))
        mps.append(ChatCompletionUserMessageParam(content=query, role="user"))
        
        memory.add(Message(content=query, name=self._name, role="user"))
        response = await self._llm.generate_str(
            mps,
            request_params=RequestParams(
                use_history=False, #ignore history in llm, we added here
                systemPrompt=system_prompt
            )
        )
        if response.startswith("Error:"):
            return response
        memory.add(Message(content=response, name=self._name, role="assistant"))
        return response

    async def send_message(self, target_id: str, action: str, message: str):
        """Send a message to a target agent"""
        if not self._initialized:
            raise RuntimeError("Agent not initialized")
            
        try:
            response = await asyncio.wait_for(
                self._runtime.send_message(
                    InteractionMessage(
                        action=action,
                        content=message,
                        source=self._name
                    ),
                    AgentId(target_id, "default"),
                    sender=AgentId(self._name, "default")
                ),
                timeout=120.0  # 120 seconds timeout
            )
            print(f"Response from {target_id}: {response.content}")
            return response
        except asyncio.TimeoutError:
            print(f"Error: Message to {target_id} timed out after 120 seconds")
            return f"Error: Message to {target_id} timed out after 120 seconds"
        except Exception as e:
            print(f"Error: sending message to {target_id}: {e}")
            return f"Error: sending message to {target_id}: {e}"

    async def update_in_hub(self, state: str = "running") -> None:
        """Register the agent in the hub"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        try:
            res = await asyncio.wait_for(
                self._runtime.send_message(
                    FunctionCall(
                        id=str(uuid.uuid4()),
                        name="register_server",
                        arguments=json.dumps({
                            "name": self._name,
                            "description": self._description,
                            "config": {
                                "type": "agent",
                                "transport": "aip-grpc",
                                "state": state,
                                "timestamp": datetime.datetime.now().isoformat()
                                }
                        }),
                    ),
                    AgentId("config_hub", "default"),
                    sender=AgentId(self._name, "default")
                ),
                timeout=30.0  
            )
            print(f"Response from config_hub: {res}")
        except asyncio.TimeoutError:
            print("Update in hub timed out after 30 seconds")
            raise
        except Exception as e:
            print(f"Error updating in hub: {e}")
            raise

    async def load_server(self, server_name: str, url: str) -> None:
        """Load a server from the hub"""
        if not self._runtime:
            raise RuntimeError("Runtime not initialized")
        
        try:
            await asyncio.wait_for(
                self._mcp_agent.load_server(server_name, url),
                timeout=30.0 
            )
        except asyncio.TimeoutError:
            print(f"Loading server {server_name} timed out after 30 seconds")
            raise
        except Exception as e:
            print(f"Error loading server {server_name}: {e}")
            raise

    async def set_system_prompt(self, system_prompt: str) -> None:
        """Set the system prompt for the agent"""
        if not self._initialized:
            raise RuntimeError("Agent not initialized")
        self._mcp_agent.instruction = system_prompt

    async def stop_when_signal(self) -> None:
        """Wait for the agent to stop"""
        if self._initialized:
            await self._runtime.stop_when_signal()

    async def stop(self) -> None:
        """Stop the agent and cleanup resources"""
        if self._initialized:
            try:
                await self.update_in_hub(state="stopped")    
            except Exception:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        self._running = False
        self._initialized = False
        await self._runtime.stop()
        




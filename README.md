# AIP Agent

## Design

The Agent System is an innovative framework that stands at the intersection of distributed systems, blockchain technology, and artificial intelligence. It is designed to facilitate a structured and secure method of interaction among autonomous entities known as agents. The system's core is defined by three principal components: an agent interaction protocol, blockchain-based authorization, and direct invocation by Large Language Models (LLMs).

### 1. Agent Interaction Protocol

The Agent Interaction Protocol is the backbone of the system, enabling seamless communication and collaboration between agents. It standardizes the way agents exchange information and perform tasks, ensuring consistency and predictability in their interactions.

- **Agent Hub**: Serves as the central hub for agent coordination and control.
  - **Permission Management**: Utilizes blockchain to authenticate and authorize agent access, ensuring secure interactions.
  - **Configuration Management**: Manages agent configurations for efficient operation and query handling.
  - **Memory Management**: Provides a global memory space for storing agent configurations, dialogue history, and prompt information.
  - **Data Storage**: Facilitates decentralized data backup to protect against data loss.

### 2. Blockchain-Based Authorization

The system leverages blockchain technology to implement a robust and transparent authorization mechanism.

- **Agent Identity Management**: Agents are registered on the blockchain with a unique UUID, linking them to specific addresses and granting them a verifiable identity.
  - **Chain-based Contract**: Records agent account information, token details, and permission settings, including read/write access and timeouts.
  - **Permission Verification**: Ensures that only authorized agents can read from or write to the shared memory, as dictated by blockchain records.

### 3. Direct Invocation by LLMs

The system is architected to be directly callable by LLMs, enhancing the capabilities of these models and enabling them to perform complex tasks through agent interactions.

- **Agent Tools Integration**: Agents are designed to be accessible as tools for LLMs, allowing these models to leverage the agents' functionalities for a wide range of applications.

## Usage

### Installation

```shell
pip install git+https://github.com/unibaseio/aip-agent.git
# or clone into local
git clone https://github.com/unibaseio/aip-agent.git
cd aip-agent
# install dependencies
uv venv
uv sync --dev --all-extras
```

### Requirements

- MEMBASE_ID must be unique for each instance
- MEMBASE_ACCOUNT must have balance in BNB testnet

### Examples

- more examples in examples dir

#### Running Tools Example

```shell
export MEMBASE_ID="<membase uuid>"
export MEMBASE_ACCOUNT="<membase account>"
export MEMBASE_SECRET_KEY="<membase secret key>"
cd examples/aip_tools
# Start the tool server for other agents to use
uv run grpc_mock_tool.py
```

#### Running Agents

```shell
export MEMBASE_ID="<membase uuid>"
export MEMBASE_ACCOUNT="<membase account>"
export MEMBASE_SECRET_KEY="<membase secret key>"
cd examples/aip_agents
# You can search/connect to other agents/tools
# For example, connect to the mock_tool above
uv run grpc_full_agent.py
```

### Python Code Examples

#### Full Agent Example

The `FullAgentWrapper` is designed to create a complete agent with LLM capabilities and memory management. Here's how to use it:

```python
from aip_agent.agents.full_agent import FullAgentWrapper
from aip_agent.agents.custom_agent import CallbackAgent
import os

async def main():
    # Initialize the full agent
    full_agent = FullAgentWrapper(
        agent_cls=CallbackAgent,  # Your custom agent implementation
        name=os.getenv("MEMBASE_ID"),  # Unique identifier
        description="You are an assistant",  # Agent description
        host_address="membase_hub_address"  # Network address
    )

    # Initialize the agent (this will:
    # 1. Register membase_id on blockchain
    # 2. Register in membase hub
    # 3. Connect to membase memory hub)
    await full_agent.initialize()

    # Process user queries
    response = await full_agent.process_query("Hello, how can you help me?")
    print(response)

    # Stop the agent when needed
    await full_agent.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

#### Tool Agent Example

The `ToolAgentWrapper` is designed to manage and execute tools in the agent system. Here's how to use it:

```python
from aip_agent.agents.tool_agent import ToolAgentWrapper
from autogen_core.tools import Tool, FunctionTool
from typing import List, Annotated
import random
import os

async def main():
    # Define your tools
    def get_weather(
        city: Annotated[str, "The city name"],
        date: Annotated[str, "The date"],
    ) -> str:
        weather = random.choice(["sunny", "cloudy", "rainy", "snowy"])
        return weather + " in " + city + " on " + date

    local_tools: List[Tool] = [
        FunctionTool(
            get_weather,
            name="get_weather",
            description="Get the weather of a city on a specific date.",
        ),
    ]

    tool_agent = ToolAgentWrapper(
        name=os.getenv("MEMBASE_ID"),
        tools=local_tools,
        host_address="membase_hub_address",
        description="This is a tool agent that can get the weather of a city on a specific date."
    )
    await tool_agent.initialize()
    await tool_agent.stop_when_signal()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Key Features

#### FullAgentWrapper Features

1. **LLM Integration**

   - Built-in LLM support for natural language processing
   - Customizable response generation
   - Context-aware conversations
   - Direct LLM invocation capabilities

2. **Tool Management**

   - Dynamic tool loading and management
   - Tool discovery and registration
   - Tool execution with parameter validation
   - Tool result processing

3. **Memory Management**

   - Persistent memory storage
   - Conversation history tracking
   - Context preservation
   - Memory-based learning

4. **Membase Hub Integration**

   - Seamless connection to membase hub
   - Remote service discovery
   - Distributed communication and coordination

5. **Message Handling & Security**

   - Asynchronous message processing
   - Message validation and verification
   - Secure message routing
   - Custom message handlers

6. **Blockchain Integration**
   - Automatic blockchain registration
   - Identity management
   - Permission-based access control
   - Secure authorization

#### ToolAgentWrapper Features

1. **Tool Management**

   - Tool registration and exposure
   - Tool capability advertisement
   - Parameter validation
   - Execution monitoring

2. **Membase Hub Integration**

   - Service discovery
   - Tool capability exposure
   - Remote accessibility and coordination

3. **Message Handling & Security**

   - Message validation
   - Secure message processing
   - Request verification
   - Response formatting

4. **Blockchain Integration**
   - Blockchain identity registration
   - Permission management
   - Access control
   - Authorization verification

## Development

### Project Structure

````

### Running Tests

```shell
pytest tests/
````

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

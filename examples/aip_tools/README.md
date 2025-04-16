# AIP Tools Server

This repository provides exmaple tool servers for the AIP system, allowing agents to access and utilize various tools through different communication protocols.

## Overview

AIP additionally supports three distinct types of tool servers:

1. **MCP**: Legacy MCP tool, start at agent startup
1. **gRPC Tool Server**: Provides indirect access to tools through gRPC protocol
2. **SSE Tool Server**: Offers direct access to tools through Server-Sent Events (SSE)

## Prerequisites

Before starting the tool servers, ensure you have the following environment variables set:

```shell
export MEMBASE_ID="<membase uuid>"
export MEMBASE_ACCOUNT="<membase account>"
export MEMBASE_SECRET_KEY="<membase secret key>"
export MEMBASE_SSE_URL="public endpoint URL" #Required for SSE tools
```

## Tool Server Setup

### 1. Legacy MCP Tool

modify aip_agent.config.yaml, add your tool configuration in mcp.servers


```yaml
mcp:
  servers:
    agent_hub:
      transport: "aip-sse"
      url: "http://127.0.0.1:8080"
    membase:
      command: uv
      args: [
        "--directory",
        "../../../membase-mcp",
        "run",
        "src/membase_mcp/server.py",
      ]
      env:
        MEMBASE_ACCOUNT: membase-mcp-test
        MEMBASE_CONVERSATION_ID: conversation_test
        MEMBASE_ID: mcp
```

### 2. gRPC Tool Server (Indirect Access)

The gRPC tool server provides a more traditional RPC-based approach for tool access.

#### Configuration
- Default grpc server: `13.212.116.103:8081`
- Supports verbose logging for debugging

#### Starting the Server
```shell
cd examples/aip_tools
# Start the tool server for other agents to use
uv run grpc_mock_tool.py
```

### 3. SSE Tool Server (Direct Access)

The SSE tool server provides real-time, event-driven access to tools.

#### Configuration
- Default host: `0.0.0.0`
- Default port: `8080`
- Requires SSE URL configuration

```shell
export MEMBASE_SSE_URL="<http://your_ip:your_port>"
```

#### Starting the Server
```shell
cd examples/aip_tools
# Start the tool server with default settings
uv run sse_mock_tool.py

# Start with custom port
uv run sse_mock_tool.py --port=<your_port>
```

## Example Tools

### gRPC Tool Server
- `get_weather`: Get weather information for a specific city and date
- `get_date`: Get the current date

### SSE Tool Server
- `calculate`: Perform basic arithmetic calculations

## Notes
- Ensure all required environment variables are set before starting the servers
- The servers must be accessible to the agents that need to use them
- For production use, consider using secure connections and proper authentication
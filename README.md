# AIP Agent

## design

The Agent System is an innovative framework that stands at the intersection of distributed systems, blockchain technology, and artificial intelligence. It is designed to facilitate a structured and secure method of interaction among autonomous entities known as agents. The system's core is defined by three principal components: an agent interaction protocol, blockchain-based authorization, and direct invocation by Large Language Models (LLMs). Here is an in-depth look at these core aspects and their respective modules:

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
- **Storage**: The storage module is crucial for the integrity of the system, providing the following services:
  - **Data Backup**: Uploads memory data to a secure storage system, ensuring data reliability and persistence.
  - **Data Recovery**: Offers the ability to retrieve data from storage in the event of loss or system migration, maintaining the system's resilience.
    In essence, the Agent System is built on a triad of foundational elements: a standardized interaction protocol for agents, a secure and transparent authorization process via blockchain, and seamless integration with LLMs for advanced functionality. This combination creates a powerful and versatile platform capable of driving complex, AI-assisted operations.

## Usage

```shell
# install dependencies
uv venv
uv sync --dev --all-extras

# server side:
# each server has
export MEMBASE_ID="<memory uuid>"
export MEMBASE_ACCOUNT="<memory account>"
export MEMBASE_SECRET_KEY="<memory secret key>"
# memory
uv run examples/aip_servers/chroma.py --port 8080
# twitter
# addtional env
export TWITTER_USERNAME = "<your username>"
export TWITTER_EMAIL = '<your email>'
export TWITTER_PASSWORD = '<your password>'
export MEMBASE_URL='http://0.0.0.0:8081'
uv run examples/aip_servers/twitter.py --port 8081

# client side usage example:
export MEMBASE_ID="<agent uuid>"
export MEMBASE_ACCOUNT="<agent account>"
export MEMBASE_SECRET_KEY="<agent secret key>"
# modify aip_agent.config.yaml
cd examples/aip_agent_config
uv run client.py
# query twitter server in llm chat
# connect twitter server in llm chat
# use tools of twitter server in llm chat
```

## Components

### Authorization

The Authorization Module is responsible for managing access control in a system where agent clients interact with a memory server. The module ensures that the identity of the client is verified and that they possess the necessary permissions to perform specific actions or access certain data.

Client-Side:

- The client generates a pair of cryptographic keys: a private key, which is kept secret, and a public key, which can be register on chain.
- When the client needs to authenticate with the server, it creates a digital signature by signing a message with its private key using the ECDSA algorithm.
- The client then sends the signed message along with its public key to the server.

Server-Side:

- Check the public key is in whitelist on chain.
- Uses the public key to verify the signature.
- If the signature is valid, the client is granted access to the requested resources or services.

### Resources

The server provides memory storage and retrieval through Chroma's vector database:

- Stores memory with content and metadata
- Persists data in `src/aip_chroma/data` directory
- Supports semantic similarity search

### Tools

The server implements CRUD operations and search functionality:

#### Memory Management

- `create_memory`: Create a new memory

  - Required: `memory_id`, `content`
  - Optional: `metadata` (key-value pairs)
  - Returns: Success confirmation
  - Error: Already exists, Invalid input

- `read_memory`: Retrieve a memory by ID

  - Required: `memory_id`
  - Returns: Memory content and metadata
  - Error: Not found

- `update_memory`: Update an existing memory

  - Required: `memory_id`, `content`
  - Optional: `metadata`
  - Returns: Success confirmation
  - Error: Not found, Invalid input

- `delete_memory`: Remove a memory

  - Required: `memory_id`
  - Returns: Success confirmation
  - Error: Not found

- `list_memory`: List all memory
  - Optional: `limit`, `offset`
  - Returns: List of memory with content and metadata

#### Search Operations

- `search_similar`: Find semantically similar memory
  - Required: `query`
  - Optional: `num_results`, `metadata_filter`, `content_filter`
  - Returns: Ranked list of similar memory with distance scores
  - Error: Invalid filter

## Features

- **Semantic Search**: Find memory based on meaning using Chroma's embeddings
- **Metadata Filtering**: Filter search results by metadata fields
- **Content Filtering**: Additional filtering based on memory content
- **Persistent Storage**: Data persists in local directory between server restarts
- **Error Handling**: Comprehensive error handling with clear messages
- **Retry Logic**: Automatic retries for transient failures

## Error Handling

The server provides clear error messages for common scenarios:

- `Memory already exists [id=X]`
- `Memory not found [id=X]`
- `Invalid input: Missing memory_id or content`
- `Invalid filter`
- `Operation failed: [details]`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

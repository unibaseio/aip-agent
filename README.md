# Chroma AIP Server

An Agent Interoperability Protocol (AIP) server implementation that provides memory management through Chroma. This server enables semantic memory search, metadata filtering, and memory management with persistent storage.

## design

The Agent Interoperability Protocol (AIP) is a sophisticated system designed to facilitate the seamless integration and interaction of AI agents within blockchain networks. AIP consists of three key modules that enable the efficient and secure operation of AI services.

1. AIP Chain:
   - This module is the interface between the AIP system and the blockchain network. It enables real-time interaction and communication, allowing the AIP system to register entities, execute transactions, and access data stored on the blockchain. The Chain Interaction component ensures that all operations are recorded and verified on the blockchain, maintaining transparency and security.
   - This module is responsible for the authentication and authorization of entities within the AIP system. It leverages cryptographic proofs to verify the identity of AIP Agents and AIP Servers, ensuring that only authorized entities can access and interact with the system. This module is crucial for maintaining the integrity and security of the AIP ecosystem.
2. AIP Chroma (An Instance of AIP Server):
   - AIP Chroma is an exemplar of an AIP Server that is specifically designed for memory management. Upon startup, AIP Chroma registers itself on the blockchain, making its services discoverable and accessible to AIP Agents. It manages the memory resources required for AI processing and ensures that the system operates efficiently.
3. AIP Agent (As an LLM Agent):
   - The AIP Agent, acting as an LLM (Large Language Model) Agent, is a key component that registers itself on the blockchain, obtains the necessary authorization, and links with an AIP Server like AIP Chroma. Once connected, the AIP Agent can utilize the tools and capabilities provided by the AIP Server to perform tasks such as natural language processing, generation, and other AI-driven functionalities. The AIP Agent's registration and authorization process ensure that it is a trusted entity within the AIP ecosystem.

Together, these modules form the AIP system, which enables the secure and efficient interoperability of AI agents within blockchain networks, promoting a new era of decentralized and intelligent applications.

## Usage

```shell
# install dependencies
uv venv
uv sync --dev --all-extras

# server side:
export MEMBASE_ID="<memory uuid>"
export MEMBASE_ACCOUNT="<memory account>"
export MEMBASE_SECRET_KEY="<memory secret key>"
uv run src/aip_chroma/server.py

# client side usage example:
export MEMBASE_ID="<agent uuid>"
export MEMBASE_ACCOUNT="<agent account>"
export MEMBASE_SECRET_KEY="<agent secret key>"
uv run examples/client.py http://0.0.0.0:8080/
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

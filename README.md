# Chroma AIP Server

An Agent Interoperability Protocol (AIP) server implementation that provides memory management through Chroma. This server enables semantic memory search, metadata filtering, and memory management with persistent storage. 

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
uv run src/client.py http://0.0.0.0:8080/
```

## Components

### Authorization

The Authorization Module is responsible for managing access control in a system where agent clients interact with a memory server. The module ensures that the identity of the client is verified and that they possess the necessary permissions to perform specific actions or access certain data.

Client-Side: 
+ The client generates a pair of cryptographic keys: a private key, which is kept secret, and a public key, which can be register on chain.
+ When the client needs to authenticate with the server, it creates a digital signature by signing a message with its private key using the ECDSA algorithm.
+ The client then sends the signed message along with its public key to the server.

Server-Side:
+ Check the public key is in whitelist on chain. 
+ Uses the public key to verify the signature.
+ If the signature is valid, the client is granted access to the requested resources or services.

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

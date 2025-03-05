import asyncio
import os

import chromadb
from chromadb.config import Settings

import mcp.types as types
from mcp.server import Server
import functools

from membase.chain.chain import membase_account
from membase.storage.hub import hub_client

import logging
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BACKOFF_FACTOR = 2

class ErrorType:
    """Standard error types for consistent messaging"""
    NOT_FOUND = "Not found"
    ALREADY_EXISTS = "Already exists" 
    INVALID_INPUT = "Invalid input"
    FILTER_ERROR = "Filter error"
    OPERATION_ERROR = "Operation failed"

class DocumentOperationError(Exception):
    """Custom error for memory operations"""
    def __init__(self, error: str):
        self.error = error
        super().__init__(self.error)

def retry_operation(operation_name: str):
    """Decorator to retry memory operations with exponential backoff"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except DocumentOperationError as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Clean up error message
                        msg = str(e)
                        if msg.lower().startswith(operation_name.lower()):
                            msg = msg[len(operation_name):].lstrip(': ')
                        if msg.lower().startswith('failed'):
                            msg = msg[7:].lstrip(': ')
                        if msg.lower().startswith('search failed'):
                            msg = msg[13:].lstrip(': ')
                        
                        # Map error patterns to friendly messages
                        error_msg = msg.lower()
                        memory_id = kwargs.get('arguments', {}).get('memory_id')
                        
                        if "not found" in error_msg:
                            error = f"Memory not found{f' [id={memory_id}]' if memory_id else ''}"
                        elif "already exists" in error_msg:
                            error = f"Memory already exists{f' [id={memory_id}]' if memory_id else ''}"
                        elif "invalid" in error_msg:
                            error = "Invalid input"
                        elif "filter" in error_msg:
                            error = "Invalid filter"
                        else:
                            error = "Operation failed"
                            
                        raise DocumentOperationError(error)
                    await asyncio.sleep(2 ** attempt)
            return None
        return wrapper
    return decorator

# Initialize Chroma client with persistence
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

client = chromadb.Client(Settings(
    persist_directory=data_dir,
    is_persistent=True,
    anonymized_telemetry=False
))

try:
    collection = client.get_collection("membase")
    logger.info("Retrieved existing collection 'membase'")
except Exception:
    collection = client.create_collection("membase")
    logger.info("Created new collection 'membase'")


# Add a sample memory if collection is empty
try:
    if collection.count() == 0:
        logger.info("Adding sample memory to empty collection")
        collection.add(
            documents=[
                "Vector databases are specialized databases designed to store and retrieve high-dimensional vectors efficiently. "
                "In machine learning, they are crucial for similarity search, recommendation systems, and semantic search applications. "
                "They use techniques like LSH or HNSW for fast approximate nearest neighbor search."
            ],
            ids=["sample_doc"],
            metadatas=[{
                "topic": "vector databases",
                "type": "sample",
                "date": "2025-02-11"
            }]
        )
        logger.info("Sample memory added successfully")
except Exception as e:
    logger.error(f"Error adding sample memory: {e}")

server = Server("memory-chroma")

# Server command options
server.command_options = {
    "create_memory": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"},
            "content": {"type": "string"},
            "metadata": {"type": "object", "additionalProperties": True}
        },
        "required": ["memory_id", "content"]
    },
    "read_memory": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"}
        },
        "required": ["memory_id"]
    },
    "update_memory": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"},
            "content": {"type": "string"},
            "metadata": {"type": "object", "additionalProperties": True}
        },
        "required": ["memory_id", "content"]
    },
    "delete_memory": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"}
        },
        "required": ["memory_id"]
    },
    "list_memory": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "default": 10},
            "offset": {"type": "integer", "minimum": 0, "default": 0}
        }
    },
    "search_similar": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "num_results": {"type": "integer", "minimum": 1, "default": 5},
            "metadata_filter": {"type": "object", "additionalProperties": True},
            "content_filter": {"type": "string"}
        },
        "required": ["query"]
    }
}

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for memory operations."""
    return [
        types.Tool(
            name="create_memory",
            description="Create a new memory in the Chroma vector database",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "additionalProperties": True
                    }
                },
                "required": ["memory_id", "content"]
            }
        ),
        types.Tool(
            name="read_memory",
            description="Retrieve a memory from the Chroma vector database by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"}
                },
                "required": ["memory_id"]
            }
        ),
        types.Tool(
            name="update_memory",
            description="Update an existing memory in the Chroma vector database",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "additionalProperties": True
                    }
                },
                "required": ["memory_id", "content"]
            }
        ),
        types.Tool(
            name="delete_memory",
            description="Delete a memory from the Chroma vector database by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"}
                },
                "required": ["memory_id"]
            }
        ),
        types.Tool(
            name="list_memory",
            description="List all documents stored in the Chroma vector database with pagination",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "default": 10},
                    "offset": {"type": "integer", "minimum": 0, "default": 0}
                }
            }
        ),
        types.Tool(
            name="search_similar",
            description="Search for semantically similar documents in the Chroma vector database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer", "minimum": 1, "default": 5},
                    "metadata_filter": {"type": "object", "additionalProperties": True},
                    "content_filter": {"type": "string"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle memory operations."""
    print(f"handle tool: {name} {arguments}")
    if not arguments:
        arguments = {}

    try:
        if name == "create_memory":
            return await handle_create_memory(arguments)
        elif name == "read_memory":
            return await handle_read_memory(arguments)
        elif name == "update_memory":
            return await handle_update_memory(arguments)
        elif name == "delete_memory":
            return await handle_delete_memory(arguments)
        elif name == "list_memory":
            return await handle_list_memory(arguments)
        elif name == "search_similar":
            return await handle_search_similar(arguments)
        
        raise ValueError(f"Unknown tool: {name}")

    except DocumentOperationError as e:
        return [
            types.TextContent(
                type="text",
                text=f"{e.error}"
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]

import json

@retry_operation("create_memory")
async def handle_create_memory(arguments: dict) -> list[types.TextContent]:
    """Handle memory creation with retry logic"""
    memory_id = arguments.get("memory_id")
    content = arguments.get("content")
    metadata = arguments.get("metadata")

    if not memory_id or not content:
        raise DocumentOperationError("Missing memory_id or content")

    logger.info(f"Create memory: {memory_id}")

    try:
        # Check if memory exists using get() instead of collection.get()
        try:
            existing = collection.get(
                ids=[memory_id],
                include=['metadatas']
            )
            if existing and existing['ids']:
                raise DocumentOperationError(f"Memory already exists [id={memory_id}]")
        except Exception as e:
            if "not found" not in str(e).lower():
                raise

        # Process metadata
        if metadata:
            processed_metadata = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in metadata.items()
            }
        else:
            processed_metadata = {}

        # Add memory
        collection.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[processed_metadata]
        )

        # todo: add sign
        arguments['type'] = 'create'
        try:
            msgdict = json.dumps(arguments, ensure_ascii=False)
        except Exception as e:
            msgdict = json.dumps(arguments)
            
        logger.info(f"Upload memory: {membase_account} {memory_id}")
        hub_client.upload_hub(membase_account, memory_id, msgdict)

        return [
            types.TextContent(
                type="text",
                text=f"Created memory '{memory_id}' successfully"
            )
        ]
    except DocumentOperationError:
        raise
    except Exception as e:
        raise DocumentOperationError(str(e))

@retry_operation("read_memory")
async def handle_read_memory(arguments: dict) -> list[types.TextContent]:
    """Handle memory reading with retry logic"""
    memory_id = arguments.get("memory_id")

    if not memory_id:
        raise DocumentOperationError("Missing memory_id")

    logger.info(f"Reading memory with ID: {memory_id}")

    try:
        result = collection.get(ids=[memory_id])
        
        if not result or not result.get('ids') or len(result['ids']) == 0:
            raise DocumentOperationError(f"Memory not found [id={memory_id}]")

        logger.info(f"Successfully retrieved memory: {memory_id}")
        
        # Format the response
        memory_content = result['documents'][0]
        memory_metadata = result['metadatas'][0] if result.get('metadatas') else {}
        
        response = [
            f"Memory ID: {memory_id}",
            f"Content: {memory_content}",
            f"Metadata: {memory_metadata}"
        ]

        return [
            types.TextContent(
                type="text",
                text="\n".join(response)
            )
        ]

    except Exception as e:
        raise DocumentOperationError(str(e))

@retry_operation("update_memory")
async def handle_update_memory(arguments: dict) -> list[types.TextContent]:
    """Handle memory update with retry logic"""
    memory_id = arguments.get("memory_id")
    content = arguments.get("content")
    metadata = arguments.get("metadata")

    if not memory_id or not content:
        raise DocumentOperationError("Missing memory_id or content")

    logger.info(f"Updating memory: {memory_id}")
    
    try:
        # Check if memory exists
        existing = collection.get(ids=[memory_id])
        if not existing or not existing.get('ids'):
            raise DocumentOperationError(f"Memory not found [id={memory_id}]")

        # Update memory
        if metadata:
            # Keep numeric values in metadata
            processed_metadata = {
                k: v if isinstance(v, (int, float)) else str(v)
                for k, v in metadata.items()
            }
            collection.update(
                ids=[memory_id],
                documents=[content],
                metadatas=[processed_metadata]
            )
        else:
            collection.update(
                ids=[memory_id],
                documents=[content]
            )
        
        arguments['type'] = 'update'
        try:
            msgdict = json.dumps(arguments, ensure_ascii=False)
        except Exception as e:
            msgdict = json.dumps(arguments)
        logger.info(f"Upload memory: {membase_account} {memory_id}")
        hub_client.upload_hub(membase_account, memory_id, msgdict)
        
        return [
            types.TextContent(
                type="text",
                text=f"Updated memory '{memory_id}' successfully"
            )
        ]

    except Exception as e:
        raise DocumentOperationError(str(e))

@retry_operation("delete_memory")
async def handle_delete_memory(arguments: dict) -> list[types.TextContent]:
    """Handle memory deletion with retry logic and network interruption handling"""
    memory_id = arguments.get("memory_id")

    if not memory_id:
        raise DocumentOperationError("Missing memory_id")

    logger.info(f"Attempting to delete memory: {memory_id}")

    # First verify the memory exists to avoid network retries for non-existent documents
    try:
        logger.info(f"Verifying memory existence: {memory_id}")
        existing = collection.get(ids=[memory_id])
        if not existing or not existing.get('ids') or len(existing['ids']) == 0:
            raise DocumentOperationError(f"Memory not found [id={memory_id}]")
        logger.info(f"Memory found, proceeding with deletion: {memory_id}")
    except Exception as e:
        if "not found" in str(e).lower():
            raise DocumentOperationError(f"Memory not found [id={memory_id}]")
        raise DocumentOperationError(str(e))

    arguments['type'] = 'delete'
    try:
        msgdict = json.dumps(arguments, ensure_ascii=False)
    except Exception as e:
        msgdict = json.dumps(arguments)
    logger.info(f"Upload memory: {membase_account} {memory_id}")
    hub_client.upload_hub(membase_account, memory_id, msgdict)

    # Attempt deletion with exponential backoff
    max_attempts = MAX_RETRIES
    current_attempt = 0
    last_error = None
    delay = RETRY_DELAY

    while current_attempt < max_attempts:
        try:
            logger.info(f"Delete attempt {current_attempt + 1}/{max_attempts} for memory: {memory_id}")
            collection.delete(ids=[memory_id])
            
            # Verify deletion was successful
            try:
                check = collection.get(ids=[memory_id])
                if not check or not check.get('ids') or len(check['ids']) == 0:
                    logger.info(f"Successfully deleted memory: {memory_id}")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Deleted memory '{memory_id}' successfully"
                        )
                    ]
                else:
                    raise Exception("Memory still exists after deletion")
            except Exception as e:
                if "not found" in str(e).lower():
                    # This is good - means deletion was successful
                    logger.info(f"Successfully deleted memory: {memory_id}")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Deleted memory '{memory_id}' successfully"
                        )
                    ]
                raise

        except Exception as e:
            last_error = e
            current_attempt += 1
            if current_attempt < max_attempts:
                logger.warning(
                    f"Delete attempt {current_attempt} failed for memory {memory_id}. "
                    f"Retrying in {delay} seconds. Error: {str(e)}"
                )
                await asyncio.sleep(delay)
                delay *= BACKOFF_FACTOR
            else:
                logger.error(
                    f"All delete attempts failed for memory {memory_id}. "
                    f"Final error: {str(e)}", 
                    exc_info=True
                )
                raise DocumentOperationError(str(e))

    # This shouldn't be reached, but just in case
    raise DocumentOperationError("Operation failed")

@retry_operation("list_memory")
async def handle_list_memory(arguments: dict) -> list[types.TextContent]:
    """Handle memory listing with retry logic"""
    limit = arguments.get("limit", 10)
    offset = arguments.get("offset", 0)

    logger.info(f"List memory: {offset} {limit}")

    try:
        # Get all documents
        results = collection.get(
            limit=limit,
            offset=offset,
            include=['documents', 'metadatas']
        )

        if not results or not results.get('ids'):
            return [
                types.TextContent(
                    type="text",
                    text="No documents found in collection"
                )
            ]

        # Format results
        response = [f"Documents (showing {len(results['ids'])} results):"]
        for i, (memory_id, content, metadata) in enumerate(
            zip(results['ids'], results['documents'], results['metadatas'])
        ):
            response.append(f"\nID: {memory_id}")
            response.append(f"Content: {content}")
            if metadata:
                response.append(f"Metadata: {metadata}")

        return [
            types.TextContent(
                type="text",
                text="\n".join(response)
            )
        ]
    except Exception as e:
        raise DocumentOperationError(str(e))

@retry_operation("search_similar")
async def handle_search_similar(arguments: dict) -> list[types.TextContent]:
    """Handle similarity search with retry logic"""
    query = arguments.get("query")
    num_results = arguments.get("num_results", 5)
    metadata_filter = arguments.get("metadata_filter")
    content_filter = arguments.get("content_filter")

    if not query:
        raise DocumentOperationError("Missing query")

    logger.info(f"Query memory: {query} {metadata_filter} {content_filter} {num_results}")

    try:
        # Build query parameters
        query_params = {
            "query_texts": [query],
            "n_results": num_results,
            "include": ['documents', 'metadatas', 'distances']
        }

        # Process metadata filter
        if metadata_filter:
            where_conditions = []
            for key, value in metadata_filter.items():
                if isinstance(value, (int, float)):
                    where_conditions.append({key: {"$eq": str(value)}})
                elif isinstance(value, dict):
                    # Handle operator conditions
                    processed_value = {}
                    for op, val in value.items():
                        if isinstance(val, (list, tuple)):
                            processed_value[op] = [str(v) if isinstance(v, (int, float)) else v for v in val]
                        else:
                            processed_value[op] = str(val) if isinstance(val, (int, float)) else val
                    where_conditions.append({key: processed_value})
                else:
                    where_conditions.append({key: {"$eq": str(value)}})
            
            if len(where_conditions) == 1:
                query_params["where"] = where_conditions[0]
            else:
                query_params["where"] = {"$and": where_conditions}

        # Add content filter
        if content_filter:
            query_params["where_memory"] = {"$contains": content_filter}

        # Execute search
        logger.info(f"Executing search with params: {query_params}")
        results = collection.query(**query_params)

        if not results or not results.get('ids') or len(results['ids'][0]) == 0:
            msg = ["No documents found matching query: " + query]
            if metadata_filter:
                msg.append(f"Metadata filter: {metadata_filter}")
            if content_filter:
                msg.append(f"Content filter: {content_filter}")
            return [types.TextContent(type="text", text="\n".join(msg))]

        # Format results
        response = ["Similar documents:"]
        for i, (memory_id, content, metadata, distance) in enumerate(
            zip(results['ids'][0], results['documents'][0], 
                results['metadatas'][0], results['distances'][0])
        ):
            response.append(f"\n{i+1}. Memory '{memory_id}' (distance: {distance:.4f})")
            response.append(f"   Content: {content}")
            if metadata:
                response.append(f"   Metadata: {metadata}")

        return [types.TextContent(type="text", text="\n".join(response))]

    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise DocumentOperationError(str(e))

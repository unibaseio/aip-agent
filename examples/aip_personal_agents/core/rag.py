import os
from typing import Annotated
  
from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

from core.save import sanitize_collection_name

default_x_name = "elonmusk"

kol_rag = ChromaKnowledgeBase(
    persist_directory="./chroma_db_kol",
    collection_name="kol_database",
    membase_account=os.getenv("MEMBASE_ACCOUNT"),
    auto_upload_to_hub=True,
)

rag = ChromaKnowledgeBase(
    persist_directory="./chroma_db_kol",
    collection_name=default_x_name,
    membase_account=os.getenv("MEMBASE_ACCOUNT"),
    auto_upload_to_hub=True,
)

rags = {}
rags[default_x_name] = rag

def switch_user(
        user_name: Annotated[str, "The user name to switch to"]
        ):
    global rags, rag
    collection_name = sanitize_collection_name(user_name)

    print(f"Switching rag to user: {user_name} ({collection_name})")
    if user_name not in rags:
        rag = ChromaKnowledgeBase(
            persist_directory="./chroma_db_kol",
            collection_name=collection_name,
            membase_account=os.getenv("MEMBASE_ACCOUNT"),
            auto_upload_to_hub=True,
        )
        rags[user_name] = rag
    else:
        rag = rags[user_name]

def add_memory(
        memory_id: Annotated[str, "The memory id"],
        content: Annotated[str, "The content of the memory"],
        metadata: Annotated[dict, "The metadata of the memory"]
        ):
    
    global rag

    doc = Document(
        doc_id=memory_id,
        content=content,
        metadata=metadata,
    )

    if rag.exists(memory_id):
        rag.update_documents(doc)
    else:
        rag.add_documents(doc)

def search_similar_posts(
        query: Annotated[str, "The query to search for"],
        num_results: Annotated[int, "The number of results to return"] = 10,
        metadata_filter: Annotated[dict, "The metadata filter"] = None,
        content_filter: Annotated[str, "The content filter"] = None,
        ):
    """
    Search for similar posts to the query.
    """
    
    global rag
    print(f"Searching {rag._collection_name} for similar posts to: {query}")
    docs = rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)
    print(f"Found {len(docs)} documents")
    if len(docs) == 0:
        global kol_rag
        print(f"Searching {kol_rag._collection_name} for similar posts to: {query}")
        docs = kol_rag.retrieve(query, top_k=num_results, metadata_filter=metadata_filter, content_filter=content_filter)
        print(f"Found {len(docs)} documents in kol_rag")
    # transform docs to list, with content,metadata, and doc_id
    return [{"name": doc.doc_id, "content": doc.content, "metadata": doc.metadata} for doc in docs]

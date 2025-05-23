import os
import re
from bs4 import BeautifulSoup
import requests
import tiktoken
from typing import List, Dict, Any

from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

# Use tiktoken to calculate token count
ENCODER = tiktoken.encoding_for_model("gpt-4o-mini")

def num_tokens(text: str) -> int:
    """Calculate the number of tokens in the text"""
    return len(ENCODER.encode(text))

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Split text into chunks
    
    Args:
        text: Text to be chunked
        chunk_size: Maximum number of tokens per chunk
        overlap: Number of overlapping tokens between chunks
    
    Returns:
        List of text chunks
    """
    tokens = ENCODER.encode(text)
    chunks = []
    
    if len(tokens) <= chunk_size:
        return [text]
    
    i = 0
    while i < len(tokens):
        # Get tokens for current chunk
        chunk_end = min(i + chunk_size, len(tokens))
        chunk_tokens = tokens[i:chunk_end]
        
        # Convert back to text
        chunk_text = ENCODER.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # Move to the next chunk position, considering overlap
        i += (chunk_size - overlap)
        # Ensure i is incremental
        if i <= 0:
            i = chunk_end
            
    return chunks

def store_blog_to_db(url: str, date_str: str, collection_name: str, chunk_size: int = 500, overlap: int = 100) -> None:
    """Get blog content from URL, chunk it and store in vector database
    
    Args:
        url: Blog URL
        collection_name: Name of the collection to store in
        chunk_size: Maximum number of tokens per chunk
        overlap: Number of overlapping tokens between chunks
    """
    # Get webpage content
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Get title and content
    title = soup.title.string if soup.title else "Untitled"
    # remove title space at begin and end
    title = title.strip()
    title = re.sub(r'[^\w\-_.]', '_', title)
    # remove duplicate underscores
    title = re.sub(r'_+', '_', title)
    # remove leading and trailing underscores
    title = title.strip('_')
    print(title)
    soup_text = soup.get_text()
    # Clean text
    soup_text = re.sub(r'\nDark Mode Toggle\n', '', soup_text)
    soup_text = re.sub(r'\nSee all posts\n', '', soup_text)
    soup_text = soup_text.strip('\n')
    
    # Split into chunks
    chunks = chunk_text(soup_text, chunk_size, overlap)

    #vitalik_address = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    # Initialize ChromaKnowledgeBase
    rag = ChromaKnowledgeBase(
        persist_directory=f"./chroma_db_kol",
        collection_name=collection_name,
        membase_account=os.getenv("MEMBASE_ACCOUNT"),
        auto_upload_to_hub=True,
    )

    grag = ChromaKnowledgeBase(
        persist_directory=f"./chroma_db_kol",
        collection_name="kol_database",
        membase_account=os.getenv("MEMBASE_ACCOUNT"),
        auto_upload_to_hub=True,
    )
    
    # Store chunks in vector database
    for i, chunk in enumerate(chunks):
        doc_id = f"{url.replace('://', '_').replace('/', '_').replace('.', '_')}_{i}"
        metadata = {
            "title": title,
            "url": url,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source": "blog",
            "type": "blog",
            "created_at": date_str
        }
        
        doc = Document(
            doc_id=doc_id,
            content=chunk,
            metadata=metadata,
        )
        
        if rag.exists(doc_id):
            rag.update_documents(doc)
        else:
            rag.add_documents([doc])

        if grag.exists(doc_id):
            grag.update_documents(doc)
        else:
            grag.add_documents([doc]) 
            
    print(f"Successfully stored blog content in {len(chunks)} chunks to vector database, collection: {collection_name}")

def vitalik_blog(username: str):
    url = "https://vitalik.eth.limo/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    print(soup.prettify())
    # find all the links
    links = soup.find_all("a")
    for link in links:
        href = link.get("href")
        if href is None:
            continue
        if href.startswith("./general"):
            # ./general/2025/03/29/treering.html
            print(href)
            # get the date from the url
            date = href[10:20]
            date = date.replace("/", "_")
            print(date)

            link_url = url + href[2:]
            print(link_url)
            
            # Chunk blog content and store in vector database
            store_blog_to_db(link_url, date, username, 500, 100)
            
            #print(soup_text)
            # upload to hub
            #vitalik_address = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
            #hub_client.upload_hub(vitalik_address, title, soup_text)
            

if __name__ == "__main__":
    default_x_name = "VitalikButerin"
    vitalik_blog(default_x_name)

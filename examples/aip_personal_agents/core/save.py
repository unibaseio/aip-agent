import json
import os
from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

default_x_name = "realDonaldTrump"

def build_text(tweet):
    base = tweet["text"].strip()

    if tweet.get("quoted_tweet"):
        quoted = tweet["quoted_tweet"]
        quoted_text = quoted.get("text", "").strip()
        quoted_user = quoted.get("author", {}).get("name", "unknown")
        base += f"\n\nQuoted Tweet from @{quoted_user}:\n{quoted_text}"
    
    return base

def format_tweet(tweet):
    doc = Document(
        doc_id=tweet["id"],
        content=build_text(tweet),
        metadata={
            "post_type": "reply" if tweet.get("isReply") else 
                        "quote" if tweet.get("isQuote") else 
                        "original",
            "likeCount": tweet["likeCount"],
            "retweetCount": tweet["retweetCount"],
            "replyCount": tweet["replyCount"],
            "quoteCount": tweet["quoteCount"],
            "viewCount": tweet["viewCount"],
            "created_at": tweet["createdAt"],
            "author": tweet["author"]["name"],
            "url": tweet["url"],
            "lang": tweet["lang"],
        }
    )
    return doc

def save_tweets(user_name):
    jsonfile = f"outputs/{user_name}.json"
    with open(jsonfile, 'r') as f:
        tweets = json.load(f)
    
    rag = ChromaKnowledgeBase(
        persist_directory=f"./chroma_db_{user_name}",
        collection_name=user_name,
        membase_account=os.getenv("MEMBASE_ACCOUNT"),
        auto_upload_to_hub=True,
    )
  
    for tweet in tweets:
        doc = format_tweet(tweet)
        rag.add_documents([doc])

if __name__ == "__main__":
    save_tweets(default_x_name)
   
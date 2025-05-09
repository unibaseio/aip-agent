import json
import os
import sys
from membase.knowledge.chroma import ChromaKnowledgeBase
from membase.knowledge.document import Document

from core.format import build_text, order_tweets
from core.common import load_user_tweets

def format_tweet_to_doc(tweet):
    doc = Document(
        doc_id=tweet["id"],
        content= tweet["author"]["name"] + " tweet: " + build_text(tweet),
        metadata={
            "type": "tweet",
            "post_type": "reply" if tweet.get("isReply") else 
                        "quote" if tweet.get("isQuote") else 
                        "original",
            "likeCount": tweet["likeCount"],
            "retweetCount": tweet["retweetCount"],
            "replyCount": tweet["replyCount"],
            "quoteCount": tweet["quoteCount"],
            "viewCount": tweet["viewCount"],
            "created_at": tweet["createdAt"],
            "url": tweet["url"],
            "lang": tweet["lang"],
            "author": tweet["author"]["name"],
            "username": tweet["author"]["userName"],
            "followersCount": tweet["author"]["followers"],
            "followingCount": tweet["author"]["following"],
        }
    )
    return doc

def save_tweets_to_collection(user_name, collection_name):
    print(f"Saving tweets of {user_name} in kol database: {collection_name}")
   
    tweets = load_user_tweets(user_name)

    rag = ChromaKnowledgeBase(
        persist_directory=f"./chroma_db_kol",
        collection_name=collection_name,
        membase_account=os.getenv("MEMBASE_ACCOUNT"),
        auto_upload_to_hub=True,
    )
  
    tweets = order_tweets(tweets, True)
    for tweet in tweets:
        if rag.exists(tweet["id"]):
            #print(f"Tweet {tweet['id']} already exists in {collection_name}")
            break
        doc = format_tweet_to_doc(tweet)
        rag.add_documents([doc])
    
    tweets = order_tweets(tweets, False)
    for tweet in tweets:
        if rag.exists(tweet["id"]):
            #print(f"Tweet {tweet['id']} already exists in {collection_name}")
            break
        doc = format_tweet_to_doc(tweet)
        rag.add_documents([doc])

def save_tweets(user_name):
    print(f"Saving tweets for {user_name}")
    save_tweets_to_collection(user_name, user_name)
    common_collection_name = "kol_database"
    save_tweets_to_collection(user_name, common_collection_name)

if __name__ == "__main__":
    default_x_name = "elonmusk"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    save_tweets(default_x_name)
   
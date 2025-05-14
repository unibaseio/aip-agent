from datetime import datetime, timedelta
import json
import shutil
import sys
from apify_client import ApifyClient
import os
from typing import Optional, List, Dict

from core.format import get_reply_tweet_ids, build_text
from core.common import order_tweets, write_user_tweets, load_user_tweets

def retrieve_tweets(user_name: str, begin_date: Optional[str] = None, end_date: Optional[str] = None):
    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    if begin_date is None:
        begin_date = "2015-01-01_00:00:00_UTC"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d_%H:%M:%S_UTC")

    # parse createdAt "Thu Jan 23 18:59:22 +0000 2025" string to datetime object for proper sorting
    def parse_date(date_str):
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")

    # Load existing tweets
    existing_tweets = load_user_tweets(user_name)
    existing_tweets = order_tweets(existing_tweets)

    # get latest tweet date of existing tweets
    if len(existing_tweets) > 0:
        latest_tweet_date =  existing_tweets[-1]["createdAt"]
        # latest + 1 second
        begin_date  = (parse_date(latest_tweet_date) + timedelta(seconds=1)).strftime("%Y-%m-%d_%H:%M:%S_UTC")

    existing_ids = {tweet.get("id") for tweet in existing_tweets}

    print(f"Retrieving {user_name} tweets from {begin_date} to {end_date}")

    # Prepare the Actor input
    run_input = {
        "searchTerms": [
            f"from:{user_name} since:{begin_date} until:{end_date}",
        ],
        "maxItems": 1000,
        "queryType": "Latest",
        "since": begin_date,
        "until": end_date,
    }

    # Run the Actor and wait for it to finish
    actor_id = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
    run = client.actor(actor_id).call(run_input=run_input)

    # Fetch and process new tweets
    new_tweets = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        tweet_type = item.get("type")
        if tweet_type and tweet_type == "mock_tweet":
            continue
        tweet_id = item.get("id")
        if tweet_id is None or tweet_id == "-1":
            continue
        if tweet_id not in existing_ids:
            new_tweets.append(item)
            existing_ids.add(tweet_id)

    if len(new_tweets) == 0:
        write_user_tweets(user_name, existing_tweets)
        return None
    
    print(f"Retrieving {len(new_tweets)} new tweets")
    
    new_tweets.sort(key=lambda x: parse_date(x["createdAt"]))

    # Combine existing and new tweets
    all_tweets = existing_tweets + new_tweets
    write_user_tweets(user_name, all_tweets)

    print(f"Retrieving replied tweets for {user_name}")
    replied_ids = get_reply_tweet_ids(all_tweets)
    print(f"Retrieving {len(replied_ids)} replied tweets")
    replied_tweets = {}
    # Process 180 replied_ids at each request
    batch_size = 180
    for i in range(0, len(replied_ids), batch_size):
        batch_ids = replied_ids[i:i + batch_size]
        print(f"Retrieving batch {i//batch_size + 1} of {(len(replied_ids) + batch_size - 1)//batch_size}")
        run_input = {
            "tweetIDs": batch_ids,
        }
        run = client.actor(actor_id).call(run_input=run_input)
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            replied_tweets[item["id"]] = item

    for t in all_tweets:
        if t.get("isReply") and t.get("inReplyToId") and  t["inReplyToId"] in replied_tweets:
            t["inReplyToText"] = build_text(replied_tweets[t["inReplyToId"]])

    # Save the combined and sorted tweets
    write_user_tweets(user_name, all_tweets)

    return all_tweets

def retrieve_mentioned_tweets(user_name: str, begin_date: Optional[str] = None):
    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    if begin_date is None:
        # align to day
        begin_date = datetime.now().strftime("%Y-%m-%d_00:00:00_UTC")

    # align to day
    end_date = (datetime.strptime(begin_date, "%Y-%m-%d_%H:%M:%S_UTC") + timedelta(days=1)).strftime("%Y-%m-%d_00:00:00_UTC")

    print(f"Retrieving {user_name} mentioned tweets from {begin_date} to {end_date}")

    # Prepare the Actor input
    run_input = {
        "@": user_name,
        "maxItems": 10,
        "queryType": "Latest",
        "since": begin_date,
        "until": end_date,
    }

    # Run the Actor and wait for it to finish
    actor_id = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
    run = client.actor(actor_id).call(run_input=run_input)

    # Fetch and process new tweets
    new_tweets = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        print(item)
        new_tweets.append(item) 

    return new_tweets

if __name__ == "__main__":
    default_x_name = "elonmusk"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Retrieving tweets for {default_x_name}")
    retrieve_tweets(default_x_name)
   
    
    

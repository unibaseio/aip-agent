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
        begin_date = "2020-01-01_00:00:00_UTC"
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
        #write_user_tweets(user_name, existing_tweets)
        return None
    
    print(f"Retrieving {len(new_tweets)} new tweets")
    
    

    # Combine existing and new tweets
    all_tweets = existing_tweets + new_tweets
    all_tweets.sort(key=lambda x: parse_date(x["createdAt"]))
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
            tweet_type = item.get("type")
            if tweet_type and tweet_type == "mock_tweet":
                continue    
            replied_tweets[item["id"]] = item

    print(f"Retrieving {len(replied_tweets)} replied tweets")
    if len(replied_tweets) == 0:
        return all_tweets

    for t in all_tweets:
        if t.get("isReply") and t.get("inReplyToId") and  t["inReplyToId"] in replied_tweets:
            t["inReplyToText"] = build_text(replied_tweets[t["inReplyToId"]])

    # Save the combined and sorted tweets
    write_user_tweets(user_name, all_tweets)

    return all_tweets

def retrieve_tweets_in_batch(user_names: List[str], max_items: 1000):
    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    
    end_date = datetime.now().strftime("%Y-%m-%d_%H:%M:%S_UTC")

    # parse createdAt "Thu Jan 23 18:59:22 +0000 2025" string to datetime object for proper sorting
    def parse_date(date_str):
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")

    existing_tweets = {}
    all_ids = []
    new_tweets = {}
    search_items = []

    # Load existing tweets
    for user_name in user_names:
        new_tweets[user_name] = []
        user_tweets = load_user_tweets(user_name)
        user_tweets = order_tweets(existing_tweets)
        existing_tweets[user_name] = user_tweets
        user_ids = {tweet.get("id") for tweet in existing_tweets}
        all_ids = all_ids + user_ids

        begin_date = "2020-01-01_00:00:00_UTC"

        # get latest tweet date of existing tweets
        if len(existing_tweets) > 0:
            latest_tweet_date =  existing_tweets[-1]["createdAt"]
            # latest + 1 second
            begin_date  = (parse_date(latest_tweet_date) + timedelta(seconds=1)).strftime("%Y-%m-%d_%H:%M:%S_UTC")
        
        search_items.append(f"from:{user_name} since:{begin_date} until:{end_date}")
        print(f"Retrieving {user_name} tweets from {begin_date} to {end_date}")

    # Prepare the Actor input
    run_input = {
        "searchTerms": search_items,
        "maxItems": max_items,
        "queryType": "Latest",
    }

    # Run the Actor and wait for it to finish
    actor_id = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
    run = client.actor(actor_id).call(run_input=run_input)

    # Fetch and process new tweets
    new_tweets_count = 0
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        tweet_type = item.get("type")
        if tweet_type and tweet_type == "mock_tweet":
            continue
        tweet_id = item.get("id")
        if tweet_id is None or tweet_id == "-1":
            continue
        if tweet_id not in all_ids:
            user_name = item.get('author', {}).get('userName', 'unknown')
            if user_name not in user_names:
                continue
            new_tweets[user_name].append(item)
            all_ids.add(tweet_id)
            new_tweets_count+=1

    if new_tweets_count == 0:
        #write_user_tweets(user_name, existing_tweets)
        return None
    
    print(f"Retrieving {new_tweets_count} new tweets")

    # Combine existing and new tweets
    updated_users = []
    replied_ids = []
    for user_name in user_names:
        if new_tweets[user_name] > 0:
            all_tweets = existing_tweets[user_name] + new_tweets[user_name]
            all_tweets.sort(key=lambda x: parse_date(x["createdAt"]))
            write_user_tweets(user_name, all_tweets)
            existing_tweets[user_name] = all_tweets
            updated_users.append(user_name)
            new_replied_ids = get_reply_tweet_ids(all_tweets)
            replied_ids = replied_ids + new_replied_ids
 
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
            tweet_type = item.get("type")
            if tweet_type and tweet_type == "mock_tweet":
                continue    
            replied_tweets[item["id"]] = item

    print(f"Retrieved {len(replied_tweets)} replied tweets")
    if len(replied_tweets) == 0:
        return updated_users
    
    for user_name in user_names:
        all_tweets = existing_tweets[user_name]
        for t in all_tweets:
            if t.get("isReply") and t.get("inReplyToId") and  t["inReplyToId"] in replied_tweets:
                t["inReplyToText"] = build_text(replied_tweets[t["inReplyToId"]])

        # Save the combined and sorted tweets
        write_user_tweets(user_name, all_tweets)

    return updated_users

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
   
    
    

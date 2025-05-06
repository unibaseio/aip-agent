import json
from datetime import datetime, timedelta
import os

def load_tweets(user_name):
    """Load existing tweets from local file if it exists."""
    file_path = f"outputs/{user_name}_tweets.json"
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"load tweets fail: {str(e)}")
    
    return []

def order_tweets(tweets, reverse=False):
    # parse createdAt string to datetime object for proper sorting
    def parse_date(date_str):
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    
    return sorted(tweets, key=lambda x: parse_date(x["createdAt"]), reverse=reverse)

def load_tweets_within(user_name: str, days: int):
    tweets = load_tweets(user_name)
    
    # filter tweets to get latest 3m 
    three_months_ago = datetime.now().astimezone() - timedelta(days=days)
    recent_tweets = [
        tweet for tweet in tweets 
        if datetime.strptime(tweet["createdAt"], "%a %b %d %H:%M:%S %z %Y") > three_months_ago
    ]
    
    return order_tweets(recent_tweets)

def clean_text(text):
    import re
    text = re.sub(r"http\S+", "", text)     # remove URLs
    text = re.sub(r"@\w+", "", text)        # remove mentions
    text = re.sub(r"#\w+", "", text)        # remove hashtags
    return text.strip()

def build_text(tweet):
    base = tweet["text"].strip()

    if tweet.get("quoted_tweet"):
        quoted = tweet["quoted_tweet"]
        quoted_text = quoted.get("text", "").strip()
        quoted_user = quoted.get("author", {}).get("userName", "unknown")
        base += f"\nQuoted from @{quoted_user}:\n{quoted_text}"
    
    if tweet.get("inReplyToId") and tweet.get("inReplyToText"):
        reply_user = tweet.get("inReplyToUsername", "unknown")
        reply_text = tweet.get("inReplyToText", "").strip()
        base += f"\nReply to @{reply_user}: \n{reply_text}"

    base += "\n\n"

    return base


def filter_tweets(tweets):
    return [
        {
            #"id": t["id"],
            "text": build_text(t),
            "post_type": "reply" if t.get("isReply") else 
                        "quote" if t.get("isQuote") else 
                        "original",
            "created_at": t["createdAt"],
            "like_count": t["likeCount"],
            "retweet_count": t["retweetCount"],
            "reply_count": t["replyCount"],
            "quote_count": t["quoteCount"],
            "view_count": t["viewCount"]
        }
        for t in tweets
        if len(t["text"]) > 10 or (t["likeCount"] + t["retweetCount"] + t["replyCount"] + t["viewCount"] + t["quoteCount"]> 1)
    ]

def get_reply_tweet_ids(tweets):
    # and the tweet ids that they are replying to
    reply_ids = []
    for t in tweets:
        if t.get("isReply") and t.get("inReplyToId"):
            if t.get("inReplyToText"):
                continue
            if t["inReplyToId"] in reply_ids:
                continue
            reply_ids.append(t["inReplyToId"])
    return reply_ids

def load_reply_tweets():
    jsonfile = f"outputs/tweets_replied.json"
    with open(jsonfile, 'r') as f:
        tweets = json.load(f)
    
    reply_tweets = {}
    for t in tweets:
        reply_tweets[t["id"]] = t
    return reply_tweets


if __name__ == "__main__":
    user_name = "cz_binance"
    tweets = load_tweets(user_name)
    #filtered = filter_tweets(tweets)
    #with open(f"outputs/{user_name}_cleaned.json", "w") as f:
    #    json.dump(filtered, f, indent=2)


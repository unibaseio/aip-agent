import json
from datetime import datetime

def load_tweets(name):
    jsonfile = f"outputs/{name}_tweets.json"
    with open(jsonfile, 'r') as f:
        return json.load(f)

def clean_text(text):
    import re
    text = re.sub(r"http\S+", "", text)     # remove URLs
    text = re.sub(r"@\w+", "", text)        # remove mentions
    text = re.sub(r"#\w+", "", text)        # remove hashtags
    return text.strip()

def get_tweet_user(tweet):
    author = tweet.get("author", {})
    print(author)

def build_text(tweet):
    base = tweet["text"].strip()

    if tweet.get("quoted_tweet"):
        quoted = tweet["quoted_tweet"]
        quoted_text = quoted.get("text", "").strip()
        quoted_user = quoted.get("author", {}).get("name", "unknown")
        base += f"\nQuoted from @{quoted_user}:\n{quoted_text}"
    base += "\n\n"

    return base

def order_tweets(tweets):
    # parse createdAt string to datetime object for proper sorting
    def parse_date(date_str):
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    
    return sorted(tweets, key=lambda x: parse_date(x["createdAt"]))

def filter_tweets(tweets):
    return [
        {
            "id": t["id"],
            "created_at": t["createdAt"],
            "text": build_text(t),
            "post_type": "reply" if t.get("isReply") else 
                        "quote" if t.get("isQuote") else 
                        "original",
            "likeCount": t["likeCount"],
            "retweetCount": t["retweetCount"],
            "replyCount": t["replyCount"],
        }
        for t in tweets
        if len(t["text"]) > 10 or (t["likeCount"] + t["retweetCount"] + t["replyCount"] > 100)
    ]

if __name__ == "__main__":
    user_name = "cz_binance"
    tweets = load_tweets(user_name)
    #filtered = filter_tweets(tweets)
    #with open(f"outputs/{user_name}_cleaned.json", "w") as f:
    #    json.dump(filtered, f, indent=2)
    if len(tweets) > 0:
        get_tweet_user(tweets[0])

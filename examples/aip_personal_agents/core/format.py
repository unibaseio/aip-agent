from core.common import load_user_tweets

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


if __name__ == "__main__":
    user_name = "cz_binance"
    tweets = load_user_tweets(user_name)
    filtered = filter_tweets(tweets)
    print(filtered)
   


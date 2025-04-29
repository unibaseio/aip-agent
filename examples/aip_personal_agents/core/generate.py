import json
import sys

from core.format import filter_tweets, order_tweets
from core.generate_prompts import build_batches, call_batch
from core.merge import merge_profiles

def generate_profile(user_name):
    print(f"Generating profile for {user_name}")
    jsonfile = f"outputs/{user_name}_tweets.json"
    with open(jsonfile, 'r') as f:
        tweets = json.load(f)
    
    ordered_tweets = order_tweets(tweets)
    if len(ordered_tweets) == 0:
        raise Exception("no tweets") 

    user_info = ordered_tweets[-1].get("author", {})

    filtered_tweets = filter_tweets(ordered_tweets)
    # print first reply and quote tweet
    for t in filtered_tweets:
        if t.get("post_type") == "reply":
            print(t)
            break

    for t in filtered_tweets:
        if t.get("post_type") == "quote":
            print(t)
            break        

    batches = build_batches(filtered_tweets)
    
    results = []
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)}")
        result = call_batch(user_info, batch)
        results.append(result)

    merged_text = "\n\n".join(results)
    final = merge_profiles(merged_text)
    with open(f"outputs/{user_name}_profile_final.json", "w") as f:
        f.write(final)

if __name__ == "__main__":
    default_x_name = "VitalikButerin"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Processing {default_x_name}")
    generate_profile(default_x_name)

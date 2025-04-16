import json
import sys

from core.clean import filter_tweets, order_tweets
from core.generate_prompts import build_batches, call_batch
from core.merge import merge_profiles

def generate_profile(user_name):
    print(f"Generating profile for {user_name}")
    jsonfile = f"outputs/{user_name}.json"
    with open(jsonfile, 'r') as f:
        tweets = json.load(f)
    
    ordered_tweets = order_tweets(tweets)
    for i in range(10):
        print(f"Ordered tweets: {ordered_tweets[i]['createdAt']}")
    filtered_tweets = filter_tweets(ordered_tweets)

    batches = build_batches(filtered_tweets)
    
    results = []
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)}")
        result = call_batch(batch)
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

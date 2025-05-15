import json
import sys

from core.format import filter_tweets
from core.generate_prompts import build_batches, call_batch
from core.merge import merge_profiles
from core.common import load_user_profile, write_user_profile, load_user_tweets, order_tweets
from core.utils import convert_to_json

def generate_profile(user_name):
    print(f"Generating profile for {user_name}")

    tweets = load_user_tweets(user_name)
    if len(tweets) == 0:
        return 
    
    ordered_tweets = order_tweets(tweets, reverse=True)
    
    user_info = ordered_tweets[0].get("author", {})

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
    profile_final = merge_profiles(merged_text)
    # check final is valid json, then write
    try:
        if not profile_final or not isinstance(profile_final, str):
            raise ValueError(f"Invalid merge_profiles result: {profile_final}")
    
        # Validate JSON format and parse it
        profile_dict = convert_to_json(profile_final)
        # Write the validated JSON to file
        write_user_profile(user_name, profile_dict)
        print(f"Successfully generated profile for {user_name}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in the generated profile - {str(e)}")
        print("Raw content:", profile_final)
        raise
    except ValueError as e:
        print(f"Error: {str(e)}")
        raise

def update_profile(user_name):
    print(f"Updating profile for {user_name}")

    tweets = load_user_tweets(user_name)
    if len(tweets) == 0:
        return 
    
    ordered_tweets = order_tweets(tweets, reverse=True)
    
    user_info = ordered_tweets[0].get("author", {})

    filtered_tweets = filter_tweets(ordered_tweets)   

    batches = build_batches(filtered_tweets, max_batch=1)
    if len(batches) == 0:
        return
    if len(batches[0]) == 0:
        return
    
    new_profile = call_batch(user_info, batches[0])

    
    latest_profile = load_user_profile(user_name)

    # merge latest profile with new profile
    profile_final = merge_profiles(new_profile + "\n\n" + json.dumps(latest_profile))
    # check final is valid json, then write
    try:
        if not profile_final or not isinstance(profile_final, str):
            raise ValueError(f"Invalid merge_profiles result: {profile_final}")

        # Validate JSON format and parse it
        profile_dict = convert_to_json(profile_final)
        # Write the validated JSON to file
        write_user_profile(user_name, profile_dict)
        print(f"Successfully updated profile for {user_name}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in the generated profile - {str(e)}")
        print("Raw content:", profile_final)

if __name__ == "__main__":
    default_x_name = "VitalikButerin"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Processing {default_x_name}")
    # generate_profile(default_x_name)
    update_profile(default_x_name)

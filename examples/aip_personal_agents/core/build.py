from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List

from core.generate import generate_profile
from core.retrieve import retrieve_tweets
from core.summary import summarize
from core.save import save_tweets

def get_user_xinfo(user_name: str) -> Any:
    if os.path.exists(f"outputs/{user_name}_info.json"):
        with open(f"outputs/{user_name}_info.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            info =  json.loads(content)
            return info
    
    if not os.path.exists(f"outputs/{user_name}_tweets.json"):
        return None
    
    with open(f"outputs/{user_name}_tweets.json", 'r', encoding='utf-8') as f:
        tweets = json.load(f)
        info = tweets[-1].get("author", {})
        with open(f"outputs/{user_name}_info.json", 'w', encoding='utf-8') as f:
            json.dump(info, f)
    return info

def create_user_xinfo(user_name: str):
    if not os.path.exists(f"outputs/{user_name}_tweets.json"):
        return None
    
    with open(f"outputs/{user_name}_tweets.json", 'r', encoding='utf-8') as f:
        tweets = json.load(f)
        info = tweets[-1].get("author", {})
        with open(f"outputs/{user_name}_info.json", 'w', encoding='utf-8') as f:
            json.dump(info, f)
    return info

def load_unfinished_users() -> Any:
    print(f"load unfinished users")
    users = []
    for file in os.listdir("outputs"):
        if file.endswith("_tweets.json"):
            # Remove '_summary.json' suffix to get the user name
            if file.endswith("_summary.json"):
                continue
            user_name = file[:-len("_tweets.json")]
            users.append(user_name) 
    return users

def load_user(user_name: str) -> Any:
    print(f"load user: {user_name}")
    with open(f"outputs/{user_name}_profile_final.json", 'r', encoding='utf-8') as f:
        content = f.read()
        # Remove the ```json markers if they exist
        content = content.replace('```json\n', '').replace('\n```', '')
        profile =  json.loads(content)
    if os.path.exists(f"outputs/{user_name}_summary.json"):
        with open(f"outputs/{user_name}_summary.json", 'r', encoding='utf-8') as f:
            content = f.read()
            content = content.replace('```json\n', '').replace('\n```', '')
            summary = json.loads(content)
    else:
        summary = {}
    return {"profile": profile, "summary": summary}

# user dict: name -> summary
def load_users() -> Dict[str, Any]:
    users = {}
    for file in os.listdir("outputs"):
        if file.endswith("_profile_final.json"):
            # Remove '_profile_final.json' suffix to get the user name
            user_name = file[:-len("_profile_final.json")]
            if user_name:  # Ensure we don't add empty names
                users[user_name] = load_user(user_name)
    return users

def build_user(user_name: str):
    print(f"build user: {user_name}")

    # check if profile already exists
    if os.path.exists(f"outputs/{user_name}_summary.json"):
        print(f"Profile for {user_name} already exists")
        return 
    
    # check if tweets need to be retrieved
    if not os.path.exists(f"outputs/{user_name}_tweets.json"):
        print(f"Retrieving tweets for {user_name}")
        retrieve_tweets(user_name)
    
    # generate profile if tweets exist
    if not os.path.exists(f"outputs/{user_name}_profile_final.json"):
        print(f"Generating profile for {user_name}")
        generate_profile(user_name)
    
    # after profile is generated, summarize
    if not os.path.exists(f"outputs/{user_name}_summary.json"):
        print(f"Summary profile for {user_name}")
        summarize(user_name)

def refresh_user(user_name: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(f"outputs/{user_name}_tweets_{date_str}.json"):
        print(f"already retrieved at {date_str} for: {user_name}")
        return
    print(f"Refreshing user: {user_name} at: {date_str}")
    retrieve_tweets(user_name)
    save_tweets(user_name)
    generate_profile(user_name)
    summarize(user_name)
    create_user_xinfo(user_name)


if __name__ == "__main__":
    for file in os.listdir("outputs"):
        if file.endswith("_profile_final.json"):
            # Remove '_profile_final.json' suffix to get the user name
            user_name = file[:-len("_profile_final.json")]
            # rename user.json to user_tweets.json
            if os.path.exists(f"outputs/{user_name}.json"):
                print(f"Renaming {user_name}.json to {user_name}_tweets.json")
                os.rename(f"outputs/{user_name}.json", f"outputs/{user_name}_tweets.json")
    
    default_x_name = "VitalikButerin"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Processing {default_x_name}")
    info = get_user_xinfo(default_x_name)
    print(info)
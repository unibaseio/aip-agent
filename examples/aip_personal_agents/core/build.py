from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List

from core.generate import generate_profile
from core.retrieve import retrieve_tweets
from core.summary import summarize
from core.format import load_tweets
from core.rate import estimate

def get_user_xinfo(user_name: str) -> Any:
    if os.path.exists(f"outputs/{user_name}_info.json"):
        with open(f"outputs/{user_name}_info.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            info =  json.loads(content)
            return info
    
    return create_user_xinfo(user_name)

def create_user_xinfo(user_name: str):
    tweets = load_tweets(user_name)
    if len(tweets) == 0:
        return {}
    
    info = tweets[-1].get("author", {})
    with open(f"outputs/{user_name}_info.json", 'w', encoding='utf-8') as f:
        json.dump(info, f)
    return info

def load_unfinished_users() -> Any:
    print(f"load unfinished users")
    users = []
    for file in os.listdir("outputs"):
        if file.endswith("_tweets.json"):
            user_name = file[:-len("_tweets.json")]
            if os.path.exists(f"outputs/{user_name}_summary.json"):
                if os.path.exists(f"outputs/{user_name}_profile_final.json"):
                    if os.path.exists(f"outputs/{user_name}_airdrop_score.json"):
                        continue        
            users.append(user_name) 
    users.sort()
    print(f"load unfinished users: {users}")
    return users

def load_user(user_name: str) -> Any:
    print(f"load user: {user_name}")
    if os.path.exists(f"outputs/{user_name}_profile_final.json"):
        with open(f"outputs/{user_name}_profile_final.json", 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove the ```json markers if they exist
            content = content.replace('```json\n', '').replace('\n```', '')
            profile =  json.loads(content)
    else:
        profile = {}

    if os.path.exists(f"outputs/{user_name}_summary.json"):
        with open(f"outputs/{user_name}_summary.json", 'r', encoding='utf-8') as f:
            content = f.read()
            content = content.replace('```json\n', '').replace('\n```', '')
            summary = json.loads(content)
    else:
        summary = {
            "detailed_analysis": {},
            "personal_brief": "No enough information or still in building...",
            "personal_tags": {
                "keywords": []
            }
        }
    if os.path.exists(f"outputs/{user_name}_airdrop_score.json"):
        with open(f"outputs/{user_name}_airdrop_score.json", 'r', encoding='utf-8') as f:
            content = f.read()
            content = content.replace('```json\n', '').replace('\n```', '')
            scores = json.loads(content)
    else:
        scores = {}
    return {"profile": profile, "summary": summary, "scores": scores}

# user dict: name -> summary
def load_users() -> Dict[str, Any]:
    users = {}
    for file in os.listdir("outputs"):
        if file.endswith("_tweets.json"):
            # Remove '_tweets.json' suffix to get the user name
            user_name = file[:-len("_tweets.json")]
            if user_name:  # Ensure we don't add empty names
                users[user_name] = load_user(user_name)
    return users

def build_user(user_name: str):
    now = datetime.now()
    print(f"Start build user: {user_name} at: {now}")

    # check if profile already exists
    if os.path.exists(f"outputs/{user_name}_summary.json"):
        if os.path.exists(f"outputs/{user_name}_profile_final.json"):
            if os.path.exists(f"outputs/{user_name}_airdrop_score.json"):
                print(f"Profiles for {user_name} already exists")
                return 
    
    # check if tweets need to be retrieved
    if not os.path.exists(f"outputs/{user_name}_tweets.json"):
        print(f"Retrieving tweets for {user_name}")
        retrieve_tweets(user_name)
    
    tweets = load_tweets(user_name)
    if len(tweets) == 0:
        print(f"Retrieving again tweets for {user_name}")
        retrieve_tweets(user_name)
        
    # generate profile if tweets exist
    if not os.path.exists(f"outputs/{user_name}_profile_final.json"):
        try:
            generate_profile(user_name)
        except Exception as e:
            print(f"Generating profile for {user_name} fail: {str(e)}")

    # after profile is generated, summarize
    if not os.path.exists(f"outputs/{user_name}_summary.json"):
        try:
            summarize(user_name)
        except json.JSONDecodeError:
            print(f"Summary profile for {user_name} fail")
            os.remove(f"outputs/{user_name}_profile_final.json")

    if not os.path.exists(f"outputs/{user_name}_airdrop_score.json"):
        print(f"Airdrop score for {user_name}")
        estimate(user_name)

    now = datetime.now()
    print(f"Finished build user: {user_name} at: {now}")

def refresh_user(user_name: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(f"outputs/{user_name}_tweets_{date_str}.json"):
        print(f"Already refreshed at {date_str} for: {user_name}")
        return
    print(f"Refreshing user: {user_name} at: {date_str}")
    tweets = retrieve_tweets(user_name)
    if tweets is None:
        return
    try:
        generate_profile(user_name)
    except Exception as e:
        print(f"Generating profile for {user_name} fail: {str(e)}")
        return

    try:
        summarize(user_name)
    except json.JSONDecodeError:
        os.remove(f"outputs/{user_name}_profile_final.json")
        return
    
    create_user_xinfo(user_name)
    estimate(user_name)


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
from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List

from core.generate import generate_profile
from core.retrieve import retrieve_tweets
from core.summary import summarize
from core.rate import estimate
from core.common import is_user_finished, is_user_tweets_exists_at, is_user_xinfo_exists, is_user_tweets_exists, is_user_profile_exists, is_user_summary_exists, is_user_airdrop_score_exists, load_user_airdrop_score, load_user_profile, load_user_summary, load_user_tweets, load_user_xinfo, load_usernames, remove_user_profile, write_user_xinfo

def get_user_xinfo(user_name: str) -> Any:
    info = load_user_xinfo(user_name)
    if info is not None and info != {}:
        return info
    
    return create_user_xinfo(user_name)

def create_user_xinfo(user_name: str):
    print(f"Creating xinfo for {user_name}")
    tweets = load_user_tweets(user_name)
    if len(tweets) == 0:
        return {}
    
    info = tweets[-1].get("author", {})
    write_user_xinfo(user_name, info)
    return info

def load_user(user_name: str) -> Any:
    print(f"load user: {user_name}")
    profile = load_user_profile(user_name)

    summary = load_user_summary(user_name)

    scores = load_user_airdrop_score(user_name)

    return {"profile": profile, "summary": summary, "scores": scores}

# user dict: name -> summary
def load_users() -> Dict[str, Any]:
    finished_users, unfinished_users = load_usernames()
    users = {}
    for user_name in finished_users:
        users[user_name] = load_user(user_name)
    for user_name in unfinished_users:
        users[user_name] = load_user(user_name)
    return users

def build_user(user_name: str):
    now = datetime.now()
    print(f"Start build user: {user_name} at: {now}")

    # check if profile already exists
    if is_user_finished(user_name):
        print(f"Profiles for {user_name} already exists")
        return 
    
    # check if tweets need to be retrieved
    if not is_user_tweets_exists(user_name):
        print(f"Retrieving tweets for {user_name}")
        retrieve_tweets(user_name)
        
    # generate profile if tweets exist
    if not is_user_profile_exists(user_name):
        try:
            generate_profile(user_name)
        except Exception as e:
            print(f"Generating profile for {user_name} fail: {str(e)}")

    # after profile is generated, summarize
    if not is_user_summary_exists(user_name):
        try:
            summarize(user_name)
        except json.JSONDecodeError:
            print(f"Summary profile for {user_name} fail")
            remove_user_profile(user_name)
            return

    # create xinfo
    if not is_user_xinfo_exists(user_name):
        create_user_xinfo(user_name)

    # estimate airdrop score
    if not is_user_airdrop_score_exists(user_name):
        estimate(user_name)

    now = datetime.now()
    print(f"Finished build user: {user_name} at: {now}")

def refresh_user(user_name: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    if is_user_tweets_exists_at(user_name, date_str):
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
        remove_user_profile(user_name)
        return
    
    create_user_xinfo(user_name)
    estimate(user_name)


if __name__ == "__main__":
    default_x_name = "VitalikButerin"
    args = sys.argv[1:]
    if len(args) > 0:
        default_x_name = args[0]
    print(f"Processing {default_x_name}")
    info = get_user_xinfo(default_x_name)
    print(info)
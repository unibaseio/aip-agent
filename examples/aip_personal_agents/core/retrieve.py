from datetime import datetime
import json
from apify_client import ApifyClient
import os

default_x_name = "taylorswift13"

def retrieve_tweets(user_name: str):
    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S_UTC")

    # Prepare the Actor input
    run_input = {
        "searchTerms": [
            f"from:{user_name} since:2024-01-01_00:00:00_UTC until:{now}",
        ],
        "maxItems": 1000,
        "queryType": "Latest",
    }


    # Run the Actor and wait for it to finish
    actor_id = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
    run = client.actor(actor_id).call(run_input=run_input)

    # Fetch and print Actor results from the run's dataset (if there are any)
    # save the results to json
    res = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        res.append(item)
    
    # save json to file
    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{user_name}.json", "w") as f:
        json.dump(res, f)
    return res

if __name__ == "__main__":
    retrieve_tweets(default_x_name)
    
    

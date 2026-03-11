import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import os
from dotenv import load_dotenv

'''
This script lists all log sets and their respective IDs.
Results are then exported to logsets.json for reference.
'''

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")

DATA_STORAGE_REGION = 'us'  # Swap for your region

# ------- [ENDPOINT SCHEMA] ------- #
# Under logsets, below are key items
# id: this is the logset id
# name: name of the logset
# logs_info: sub logset, which also contains id and name of the sublogset

def list_all_logsets(s: Session) -> None:

    url = f"https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com/management/logsets"
    headers = {"x-api-key": API_KEY}

    response = s.get(url, headers=headers)
    print("Status:", response.status_code)

    data = response.json()

    result = {
        "logsets": []
    }

    for item in data.get("logsets", []):
        logset_entry = {
            "id": item.get("id"),
            "name": item.get("name"),
            "logs_info": []
        }

        # Nest all logs under this logset
        for log in item.get("logs_info", []):
            logset_entry["logs_info"].append({
                "id": log.get("id"),
                "name": log.get("name")
            })

        result["logsets"].append(logset_entry)


    # Ensure output directory exists
    os.makedirs("outputs", exist_ok=True)

    # Write to JSON file
    output_path = "outputs/logsets.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"Logsets written to {output_path}")

if __name__ == '__main__':

    session = Session()
    session.mount(
        f'https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com',
        HTTPAdapter(max_retries=(
            # Handles rate limiting by default, by sleeping until the limit has reset before retrying.
            Retry(total=3,
                  backoff_factor=1,
                  status_forcelist=[500, 502, 503, 504])
        ))
    )
    session.close()

    list_all_logsets(session)
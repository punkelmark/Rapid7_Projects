import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv

'''
This script lists all saved queries and their respective IDs.
Results are then exported to sq_saved_queries.json for reference.
'''

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")
DATA_STORAGE_REGION = 'us'  # Swap for your region

def list_saved_queries(s: Session) -> None:
    response = s.get(f'https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com/query/saved_queries',
                     headers={'x-api-key': API_KEY})
    print(response.status_code)

    queries = []
    for item in response.json()['saved_queries']:
        queries.append({"id": item.get('id'), "name": item.get('name'), "logs": item.get('logs')})

    # Ensure output directory exists
    os.makedirs("outputs", exist_ok=True)
    # Write to JSON file
    output_path = "outputs/sq_list.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=4)

    print(f"Queries written to {output_path}")

    return queries

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
    list_saved_queries(session)

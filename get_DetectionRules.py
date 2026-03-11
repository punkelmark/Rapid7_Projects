'''
Uses following API =>
https://help.rapid7.com/insightidr/en-us/api/v2/docs.html#tag/Investigations/operation/listInvestigations

An API that retrieves a page of investigations matching given request parameters.
'''

import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import pandas as pd
from collections import Counter
import asyncio
import aiohttp

import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")
DATA_STORAGE_REGION = 'us'  # Swap for your region

size = 25
lookback = 7

def get_time_range(days_ago: int):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days_ago)
    
    # Format to ISO 8601 with 'Z' for UTC
    start_iso = start_time.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    return start_iso, end_iso

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

    url = f"https://{DATA_STORAGE_REGION}.api.insight.rapid7.com/idr/v1/rules"

    response = session.get(url, headers={'x-api-key': API_KEY}
                           # ,params = {"size": 100, "index": 2}
                           )
    body = response.json()

    # Write to JSON file
    output_path = "outputs/get_detectionrules.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=4)
    print(f"Investigation results written to {output_path}")


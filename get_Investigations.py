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

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")
DATA_STORAGE_REGION = 'us'  # Swap for your region

size = 100
lookback = 1

def get_time_range(days_ago: int):
    """
    Returns a tuple (start_time, end_time) in ISO 8601 format (UTC)
    for the given number of days ago until now.
    Example:
        get_time_range(14)
        -> ('2026-01-13T00:00:00Z', '2026-01-27T15:23:45Z')
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days_ago)
    
    # Format to ISO 8601 with 'Z' for UTC
    start_iso = start_time.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    end_iso = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    return start_iso, end_iso

async def fetch_page(session, index: int):

    start_iso, end_iso = get_time_range(lookback)

    """Fetch one page of results."""
    url = f"https://{DATA_STORAGE_REGION}.api.insight.rapid7.com/idr/v2/investigations"
    params = {
        "index": index,
        "size": size,
        "start_time": start_iso,
        "end_time": end_iso
    }
    headers = {"x-api-key": API_KEY}

    async with session.get(url, headers=headers, params=params) as resp:
        resp.raise_for_status()
        body = await resp.json()
        return body.get("data", [])


async def fetch_all_pages(concurrent_pages=5):
    """Fetch all pages concurrently."""
    all_items = []
    index = 0

    async with aiohttp.ClientSession() as session:
        while True:
            # Launch multiple pages concurrently
            tasks = [fetch_page(session, i) for i in range(index, index + concurrent_pages)]
            results = await asyncio.gather(*tasks)

            # Flatten results
            page_data = [item for sublist in results for item in sublist]

            if not page_data:
                break

            all_items.extend(page_data)
            index += concurrent_pages

    return all_items

def summarize_distinct_counts(items, keys, filter_func=None):
    """
    Returns a summary of distinct counts and occurrences for multiple keys,
    optionally filtered by a custom function.
    
    Args:
        items (list): List of dictionaries (JSON objects)
        keys (list): List of keys to analyze
        filter_func (callable, optional): Function that takes an item and returns True/False
    
    Returns:
        dict: {
            key1: {"distinct_count": int, "occurrences": {value: count, ...}},
            key2: {...},
            ...
        }
    """
    summary = {}
    
    # Apply filter if provided
    filtered_items = [item for item in items if filter_func(item)] if filter_func else items
    
    for key in keys:
        values = [item.get(key) for item in filtered_items if key in item]
        counter = Counter(values)
        sorted_counter = dict(sorted(counter.items(), key=lambda kv: kv[1], reverse=True))
        summary[key] = {
            "distinct_count": len(sorted_counter),
            "occurrences": sorted_counter
        }
    
    return summary

if __name__ == '__main__':

    all_items = asyncio.run(fetch_all_pages())

    # Get total investigations fetched for the past lookback days
    print(f"Total items fetched: {len(all_items)}")

    # Write to JSON file
    output_path = "outputs/get_investigations_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=4)
    print(f"Investigation results written to {output_path}")

    # # Write to Excel
    # df = pd.DataFrame(all_items)
    # output_file = "outputs/get_investigation_results.xlsx"
    # df.to_excel(output_file, index=False)
    # print(f"Excel file saved to {output_file}")

    keys_to_analyze = ["title"]
    result = summarize_distinct_counts(
        all_items, keys_to_analyze
        #, filter_func=lambda item: item.get("priority") == "CRITICAL"
        )
    # print(json.dumps(result, indent=4))


# Reference: https://help.rapid7.com/insightidr/en-us/api/v1/docs.html#tag/Community-Threats

import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import os
from dotenv import load_dotenv

import pandas as pd

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")
DATA_STORAGE_REGION = 'us'  # Swap for your region

def add_community_threat(s: Session, threatName, noteText, indicators) -> None:
    
    PAYLOAD = {
        'threat': threatName,
        'note': noteText,
        'indicators': indicators # in json
    }

    response = s.post(f'https://{DATA_STORAGE_REGION}.api.insight.rapid7.com/idr/v1/customthreats',
                      headers={'x-api-key': API_KEY},
                      json=PAYLOAD)
    print(response.status_code)
    print(json.dumps(response.json(), indent=4))

def getIOCs(excelFile):

    try:
        df = pd.read_excel(excelFile)

        # Prepare dictionary for storage
        indicators = {
            "ips": set(),
            "hashes": set(),
            "domain_names": set(),
            "urls": set()
        }

        # Process rows in the .xlsx file
        for _, row in df.iterrows():
            ind_type = str(row.get("type", "")).strip().lower()
            value = str(row.get("object", "")).strip()

            if not value or value.lower() == "nan":
                print("Empty cell, please provide IOC.")
                continue

            if ind_type == "ip":
                indicators["ips"].add(value)
            elif ind_type == "hash":
                indicators["hashes"].add(value)
            elif ind_type == "domain":
                indicators["domain_names"].add(value)
            elif ind_type == "url":
                indicators["urls"].add(value)

        indicators_processed = {
            "ips": sorted(list(indicators["ips"])),
            "hashes": sorted(list(indicators["hashes"])),
            "domain_names": sorted(list(indicators["domain_names"])),        
            "urls": sorted(list(indicators["urls"])),
        }

        print(indicators_processed)
        return indicators_processed

    except Exception as e:
        print("Error occured:", str(e))
        if "Permission denied" in str(e):
            print("The .xlsx file is open, please save and close.")
        return None

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

    excelfile = "sampleIOC.xlsx"
    indicators = getIOCs(excelfile)
    if indicators: 
        add_community_threat(session, "API ADDING SAMPLE AGAIN", "API ADDING SAMPLE", indicators)

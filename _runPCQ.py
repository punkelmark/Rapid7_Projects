import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import os
from dotenv import load_dotenv

'''
This script runs a pre-computed query by giving the name of the query.

get_precomputed_queries() first fetches all available PCQs and gets the matching ID with the provided PCQ name.
fetch_pcq_results() then handles the fetching of the actual data after obtaining the PCQ ID.

results are then saved in a data variable which can then be use to print or export needed data.
'''

load_dotenv()
API_KEY = os.getenv('SOC_DASHBOARD_API')
DATA_STORAGE_REGION = 'us'  # Swap for your region

def get_precomputed_queries(s: Session, target_pcq):

    # Pulls only custom pre-computed queries, saves them first in a dictionary upon fetch
    response = s.get(f'https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com/management/metrics',
                     headers={'x-api-key': API_KEY})

    pcq_list = {}
    for pcq in response.json()['metrics']: # loop through the response and save PCQ_Name:PCQ_ID in the dictionary pcq_list
        pcq_list[pcq['name']] = pcq['id']

    # if the target_pcq name is in the dictionary pcq_list requested, return the PCQ ID, else, return 0
    return pcq_list[target_pcq] if target_pcq in pcq_list else 0

def fetch_pcq_results(s: Session, target_pcq, TIME_RANGE):

    PCQ_ID = get_precomputed_queries(session, target_pcq)
    if PCQ_ID == 0: 
        print('Pre-Computed Query does not exist.') 
        return 0

    response = s.get(f"https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com/"
                     f"query/metrics/{PCQ_ID}",
                     headers={'x-api-key': API_KEY},
                     params={"time_range": TIME_RANGE})
    data = response.json()

    print("{0} total stats count for {1}: {2}".format(target_pcq, data['leql']['time_range'], data['statistics']['result']))

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

    TIME_RANGE = 'Last 12 hours'
    fetch_pcq_results(session, 'C&C Callback Communications Blocked', TIME_RANGE)
    # fetch_pcq_results(session, 'Trend Micro CnC Alerts', TIME_RANGE) # grouped by asset
    fetch_pcq_results(session, 'Malware (Desktops)', TIME_RANGE)
    fetch_pcq_results(session, 'Malware (Servers)', TIME_RANGE)
    fetch_pcq_results(session, 'Access to Malicious Sites', TIME_RANGE)
    fetch_pcq_results(session, 'Device Control Blocked Device Count', TIME_RANGE)
    fetch_pcq_results(session, 'Ransomware Behavior Detection', TIME_RANGE)
    fetch_pcq_results(session, 'Investigation Count', TIME_RANGE)

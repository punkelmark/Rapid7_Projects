import json
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")

DATA_STORAGE_REGION = 'us'  # Swap for your region

def get_healthMetrics(s: Session):

    health_metrics = {}
    resourceTypes = ['agent', 'event_sources', 'collectors', 'honeypots']

    for resource in resourceTypes:

        all_items = []
        index = 0
        size = 20

        while True:
            response = s.get(f"https://{DATA_STORAGE_REGION}.api.insight.rapid7.com/idr/v1/health-metrics",
                                headers={'x-api-key': API_KEY}, 
                                params={"index": index, "size": size, "resourceTypes": resource},
                                timeout=30
                                )
            body = response.json()

            if not body["data"]:
                break

            all_items.extend(body["data"])
            index += 1

        health_metrics[resource] = all_items

    return health_metrics

def display_healthMetrics(healthMetrics):

    resourceTypes = ['agent', 'event_sources', 'collectors', 'honeypots']

    if 'agent' in healthMetrics:
        print("\n*** Total Rapid7 Agents:", healthMetrics[resourceTypes[0]][0]['total'])
        print("Offline:", healthMetrics[resourceTypes[0]][0]['offline'])
        print("Online:", healthMetrics[resourceTypes[0]][0]['online'])
        print("Stale:", healthMetrics[resourceTypes[0]][0]['stale'])

    if 'event_sources' in healthMetrics:
        event_sources = healthMetrics[resourceTypes[1]]
        print("\n*** Total Rapid7 Event Sources:", len(event_sources))
        for source in event_sources:
            print("\nEvent Source: {0} | State: {1}\nLast Active: {2}\nIssue: {3}".format(source['name'], source['state'], source['last_active'], source['issue']))

    if 'collectors' in healthMetrics:
        collectors = healthMetrics[resourceTypes[2]]
        print("\n*** Total Rapid7 Collectors:", len(collectors))
        for collector in collectors:
            print("\nName: {0} | State: {1}\nLast Active: {2}\nEvent Sources Used: {3}\nIssue".format(collector['name'], collector['state'], collector['last_active'], collector['issue']))

    if 'honeypots' in healthMetrics:
        honeypots = healthMetrics[resourceTypes[3]]
        print("\n*** Total Rapid7 Honeypts:", len(honeypots))
        for honeypot in honeypots:
            print("\nName: {0} | State: {1}\nLast Active: {2}\nEvent Sources Used: {3}\nIssue".format(honeypot['name'], honeypot['state'], honeypot['last_active'], honeypot['issue']))

def export_healthMetrics(healthMetrics, output_file):

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

        # AGENTS
        if 'agent' in healthMetrics:
            agents_df = pd.DataFrame(healthMetrics['agent'])
            agents_df.to_excel(writer, sheet_name='Agents', index=False)

        # EVENT SOURCES
        if 'event_sources' in healthMetrics:
            event_sources_df = pd.DataFrame(healthMetrics['event_sources'])
            event_sources_df.to_excel(writer, sheet_name='Event_Sources', index=False)

        # COLLECTORS
        if 'collectors' in healthMetrics:
            collectors_df = pd.DataFrame(healthMetrics['collectors'])
            collectors_df.to_excel(writer, sheet_name='Collectors', index=False)

        # HONEYPOTS
        if 'honeypots' in healthMetrics:
            honeypots_df = pd.DataFrame(healthMetrics['honeypots'])
            honeypots_df.to_excel(writer, sheet_name='Honeypots', index=False)

    print("Export complete:", output_file)

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

    healthMetrics = get_healthMetrics(session)
    # display_healthMetrics(healthMetrics)

    export_healthMetrics(healthMetrics, "outputs/rapid7_health_metrics.xlsx")
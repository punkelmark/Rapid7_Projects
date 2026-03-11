import json
import time
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
API_KEY = os.getenv("SOC_DASHBOARD_API")

# Set query time range 30 days from now, leave FROM/TO empty if time range is specified in the saved query itself in R7
now = datetime.now(timezone.utc)
thirty_days_ago = now - timedelta(days=30)

FROM_TS_MILLIS = '' #int(thirty_days_ago.timestamp() * 1000)
TO_TS_MILLIS = ''#int(now.timestamp() * 1000)

DATA_STORAGE_REGION = 'us'  # Swap for your region

class RateLimitedException(Exception):
    def __init__(self, message: str, secs_until_reset: int):
        super().__init__(message)
        self.secs_until_reset = secs_until_reset


def is_query_in_progress(query_response: Response) -> bool:
    if 'links' not in query_response.json():
        return False
    elif 'Next' in [link['rel'] for link in query_response.json()['links']]:
        return False
    elif 'Self' in [link['rel'] for link in query_response.json()['links']]:
        return True
    raise Exception('LogSearch query returned an invalid response body according to their spec '
                    '- contains a "links" object, which does not contain a link with either '
                    '"rel" equal to "Next" or "Self"')


def poll_request_to_completion(logsearch_session: Session,
                               query_in_progress_response: Response) -> Response:
    """
    "continuation" polls expire after 10 seconds, so we must not wait too long between
    requests. However we must not poll too frequently for long-running queries or we
    risk being rate limited.
    """
    if query_in_progress_response.status_code == 429:
        secs_until_reset = query_in_progress_response.headers.get('X-RateLimit-Reset')
        raise RateLimitedException(
            f'Log Search API Key was rate limited. Seconds until rate limit reset: {secs_until_reset}',
            int(secs_until_reset)
        )

    if not is_query_in_progress(query_in_progress_response):
        return query_in_progress_response

    poll_delay_secs = 0.5
    max_poll_delay_secs = 6
    links = {link['rel']: link['href'] for link in query_in_progress_response.json()['links']}
    while 'Self' in links:
        time.sleep(poll_delay_secs)

        resp = logsearch_session.get(links['Self'], headers={'x-api-key': API_KEY})

        if resp.status_code == 429:
            secs_until_reset = resp.headers.get('X-RateLimit-Reset')
            raise RateLimitedException(
             f'Log Search API Key was rate limited. Seconds until rate limit reset: {secs_until_reset}',
             int(secs_until_reset)
            )

        if not is_query_in_progress(resp):
            return resp

        poll_delay_secs = min(poll_delay_secs * 2, max_poll_delay_secs)
        links = {link['rel']: link['href'] for link in resp.json()['links']}


def has_next_page(query_response: Response) -> bool:
    return 'links' in query_response.json() and \
           'Next' in [link['rel'] for link in query_response.json()['links']]


def get_next_page_of_results(logsearch_session: Session, resp: Response) -> Response:
    links = {link['rel']: link['href'] for link in resp.json()['links']}
    return logsearch_session.get(links['Next'], headers={'x-api-key': API_KEY})


def perform_query(logsearch_session: Session, SAVED_QUERY_ID) -> Response: # Main function that returns our reponses
    try:
        resp = poll_request_to_completion(
            logsearch_session,
            logsearch_session.get(f'https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com/'
                                  f'query/saved_query/{SAVED_QUERY_ID}',
                                  headers={'x-api-key': API_KEY},
                                  params={'from': FROM_TS_MILLIS, 'to': TO_TS_MILLIS}
                                  )
        )

        return resp
    except RateLimitedException as e:
        print(f'Log Search API Key was rate limited. Sleeping for {e.secs_until_reset} seconds')
        time.sleep(e.secs_until_reset)
        return perform_query(logsearch_session)

def _runSQ(session: Session, SAVED_QUERY_ID):
    all_results = [] # Call this list in the end of the program to retrieve complete results

    query_results_page = perform_query(session, SAVED_QUERY_ID)

    while True:
        resp_json = query_results_page.json()
        all_results.append(resp_json)

        if not has_next_page(query_results_page):
            break

        try:
            query_results_page = poll_request_to_completion(session, get_next_page_of_results(session, query_results_page))
        except RateLimitedException as e:
            print(f'Rate limited. Sleeping {e.secs_until_reset}s')
            time.sleep(e.secs_until_reset)

    # Ensure output directory exists
    os.makedirs("outputs", exist_ok=True)
    # Write to JSON file
    output_path = "outputs/sq_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4)

    print(f"Queries written to {output_path}")

if __name__ == '__main__':
    session = Session()
    session.mount(
        f'https://{DATA_STORAGE_REGION}.rest.logs.insight.rapid7.com',
        HTTPAdapter(max_retries=(
            Retry(total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                respect_retry_after_header=False)  # Rate limiting must be handled explicitly
        ))
    )

    SAVED_QUERY_ID = '00000000-0000-d5e9-0000-000000000000' # Refer to saved_queries.json, generated using _listSavedQueries.py
    _runSQ(session, SAVED_QUERY_ID)

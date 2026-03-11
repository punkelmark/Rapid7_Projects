import json
import _runSQ
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_investigation_statistics(session: Session, sq_id):
    '''
    This runs _runSQ.py which then loads results exported from sq_results.json.
    To get the sq_id, run _listSQ.py to get the list of all available saved queries with their IDs.
    '''
    _runSQ._runSQ(session, sq_id) # Run the _runSQ script through import

    # Load JSON
    with open("outputs/sq_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract raw stats safely
    raw_stats = data[0].get('statistics', {}).get('groups', [])

    # Build dictionary and sort in one line
    stats_list = {
        inv_name: info.get('count', 0)
        for item in raw_stats
        for inv_name, info in item.items()
    }

    # Sort by count (ascending)
    stats_list = dict(sorted(stats_list.items(), key=lambda kv: kv[1]))

    # Print pretty JSON
    print(json.dumps(stats_list, indent=4))

if __name__ == '__main__':

    session = Session()
    session.mount(
        f'https://us.rest.logs.insight.rapid7.com',
        HTTPAdapter(max_retries=(
            Retry(total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                respect_retry_after_header=False)  # Rate limiting must be handled explicitly
        ))
    )

    # Refer to outputs/sq_list.json, generated using _listSQ.py, this function gets investigation statistics using a saved query in R7
    investigation_stats_ID = '00000000-0000-d5e9-0000-000000000000'
    get_investigation_statistics(session, investigation_stats_ID)
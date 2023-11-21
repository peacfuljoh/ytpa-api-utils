
from typing import Optional, List, Callable, Generator
import requests
import json

import pandas as pd


def get_configs_post(endpoint: str,
                     collection: str,
                     config_name: Optional[str] = None) \
        -> List[dict]:
    """
    Get config info for a data collection and optionally verify that a given config name exists in the list of configs.
    """
    response = requests.post(endpoint, json=dict(name=collection))
    recs = json.loads(response.text)

    if config_name is not None:
        config_ids = [config_['_id'] for config_ in recs]
        assert config_name in config_ids

    return recs

def df_sender_for_insert(endpoint: str,
                         preprocess_func: Callable[[pd.DataFrame], List[dict]],
                         df_gen: Generator[pd.DataFrame, None, None],
                         print_json: bool = False):
    """Send DataFrames (from a generator) to a server-side NoSQL data store via post requests."""
    for df in df_gen:
        recs: List[dict] = preprocess_func(df)
        res = requests.post(endpoint, json=recs)
        if print_json:
            print(res.json())


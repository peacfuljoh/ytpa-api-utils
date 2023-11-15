"""Constants for API utils"""

import os

TESTING = os.environ.get('RUN_API_TESTS') == 'yes'

import queue
import json

import pandas as pd




""" websocket """
# stream termination signal
WS_STREAM_TERM_MSG = 'DONE'

# max DataFrame rows to send over websocket
WS_MAX_RECORDS_SEND = 100 if not TESTING else 2



""" info for testing """
WS_RECORDS_TESTING = [json.dumps(df) for df in [
    [{'a': 0, 'b': 7}, {'a': 1, 'b': 8}],
    [{'a': 2, 'b': 9}, {'a': 3, 'b': 10}],
    [],
    [{'a': 10, 'b': 17}, {'a': 11, 'b': 18}],
    [{'a': 12, 'b': 19}, {'a': 13, 'b': 20}],
    [],
    WS_STREAM_TERM_MSG
]]

WS_DFS_TESTING = [
    pd.DataFrame(dict(a=[0, 1, 2, 3], b=[7, 8, 9, 10])),
    pd.DataFrame(dict(a=[10, 11, 12, 13], b=[17, 18, 19, 20]))
]

DF_GEN_QUEUE = queue.Queue()

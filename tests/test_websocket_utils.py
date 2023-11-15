"""Tests for websocket utils"""

import os

os.environ['RUN_API_TESTS'] = 'yes'

import asyncio
import json

from src.ytpa_api_utils.websocket_utils import df_generator_ws, run_websocket_stream
from src.ytpa_api_utils.constants import WS_DFS_TESTING, WS_RECORDS_TESTING, DF_GEN_QUEUE




def test_df_gen_websocket_send():
    websocket = None
    setup_df_gen = None

    asyncio.run(run_websocket_stream(websocket, setup_df_gen))

    for val in WS_RECORDS_TESTING:
        assert json.loads(val) == DF_GEN_QUEUE.get()

def test_df_gen_websocket_receive():
    endpoint = ''
    msg_to_send = {}
    df_gen = df_generator_ws(endpoint, msg_to_send)

    for i, df in enumerate(df_gen):
        assert df.equals(WS_DFS_TESTING[i])


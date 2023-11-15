"""Utils for communicating over a websocket"""

import asyncio
import json
from typing import List, Union, Optional, Callable

import websockets

import pandas as pd
from fastapi import WebSocket, WebSocketDisconnect

from ytpa_utils.df_utils import df_dt_codec
from .constants import WS_STREAM_TERM_MSG, WS_MAX_RECORDS_SEND




""" SEND """
async def gen_next_records(gen, websocket: WebSocket):
    """
    Get next record from a generator if possible, otherwise send stream termination signal and shut down websocket.
    """
    try:
        return next(gen)
    except:
        # clean up and disconnect
        await websocket.send_json(WS_STREAM_TERM_MSG)
        raise WebSocketDisconnect

async def send_df_via_websocket(df: pd.DataFrame,
                                transformations: dict,
                                websocket: WebSocket):
    """Send DataFrame in pieces over websocket"""
    i = 0
    while not (df_ := df.iloc[i * WS_MAX_RECORDS_SEND: (i + 1) * WS_MAX_RECORDS_SEND]).empty:
        # apply transformations to specified columns
        if transformations is not None:
            cnvs = {key: val for key, val in transformations.items() if key in df_.columns}
            df_dt_codec(df_, cnvs, 'encode')  # make it JSONifiable

        # pack DataFrame into list of dictionaries
        data_send: List[dict] = df_.to_dict('records')

        # send data over websocket
        await websocket.send_json(data_send)

        # increment pointer
        i += 1

    # send empty list signifying that entire DataFrame has been sent
    await websocket.send_json([])

async def run_websocket_stream(websocket: WebSocket,
                               setup_df_gen: Callable,
                               transformations: Optional[dict] = None):
    """
    Run websocket stream that generates DataFrames.

    setup_df_gen is a function that returns a DataFrame generator and a database engine. The engine is destroyed before
    exiting to ensure that db connections are not left dangling.
    """
    df_gen, engine = None, None
    try:
        while True:
            # receive JSON data
            data_recv = await websocket.receive_json()

            # initialize DataFrame generator first time around
            if df_gen is None:
                df_gen, engine = setup_df_gen(data_recv)

            # generate the next DataFrame
            df = await gen_next_records(df_gen, websocket)

            # send DataFrame via websocket
            await send_df_via_websocket(df, transformations, websocket) # send DataFrame in chunks
    except WebSocketDisconnect as e:
        del df_gen, engine
        print(e)



""" RECEIVE """
async def get_next_msg(websocket: websockets.connect) -> Optional[List[dict]]:
    """Receive next message over websocket"""
    # receive data
    data_recv = await websocket.recv()
    data_recv: Union[List[dict], str] = json.loads(data_recv) # subframe of DataFrame, stream termination string, or empty list
    assert isinstance(data_recv, (list, str))

    # check for stream termination message
    if data_recv == WS_STREAM_TERM_MSG:
        raise StopIteration

    # check for empty list indicating end of DataFrame
    if len(data_recv) == 0:
        return

    return data_recv

async def receive_msgs(websocket: websockets.connect,
                       q: asyncio.Queue):
    """
    Receive sequence of data messages over websocket connection, stitch them into a DataFrame, place them in a queue.
    """
    data_recv_all = []
    while 1:
        data_recv = await get_next_msg(websocket)
        if data_recv is not None: # in middle of subframe
            data_recv_all += data_recv
        else: # finished getting DataFrame
            df = pd.DataFrame.from_dict(data_recv_all)
            await q.put(df)
            return

async def stream_dfs_websocket(endpoint: str,
                               msg_to_send: dict,
                               q: asyncio.Queue):
    """Stream data into a queue of DataFrames over a websocket."""
    msg_to_send_str = json.dumps(msg_to_send)
    async with websockets.connect(endpoint) as websocket:
        try:
            while 1:
                await websocket.send(msg_to_send_str)
                await receive_msgs(websocket, q)
        except Exception as e:
            print(e)
            await q.put(None)

async def process_dfs_stream(q_stream: asyncio.Queue,
                             options: Optional[dict] = None):
    """Process DataFrames from a queue until a None is found"""
    # options
    if options is None:
        options = {}
    print_dfs = options.get('print_df')
    print_count = options.get('print_count')
    q_stats = options.get('q_stats')

    # process stream
    count = 0
    while 1:
        df = await q_stream.get()
        if df is None:
            return
        count += len(df)
        if print_dfs:
            print(df)
        if print_count:
            print(f"Records count so far: {count}.")
        if q_stats:
            q_stats.put({'count': count})

def run_dfs_stream_with_options(endpoint: str,
                                msg_to_send: dict,
                                df_processor: Callable,
                                q_stream: asyncio.Queue):
    """Simultaneously stream data through websocket and process it."""
    async def run_tasks():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(df_processor(q_stream))
            tg.create_task(stream_dfs_websocket(endpoint, msg_to_send, q_stream))
    asyncio.run(run_tasks())


